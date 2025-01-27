# isort: skip_file
# flake8: noqa
# The import order of autogluon sub module here could cause seg fault. Ignore isort for now
# https://github.com/autogluon/autogluon/issues/2042
import argparse
import os
import pandas as pd
import shutil
from pprint import pprint

import yaml

from autogluon.common.loaders import load_pd
from autogluon.tabular import TabularPredictor, TabularDataset, FeatureMetadata


def get_input_path(path):
    file = os.listdir(path)[0]
    if len(os.listdir(path)) > 1:
        raise ValueError(f"WARN: more than one file is found in {channel} directory")
    print(f"Using {file}")
    filename = f"{path}/{file}"
    return filename


def get_env_if_present(name):
    result = None
    if name in os.environ:
        result = os.environ[name]
    return result


def prepare_timeseries_dataframe(df, predictor_init_args):
    target = predictor_init_args["target"]
    cols = df.columns.to_list()
    id_column = cols[0]
    timestamp_column = cols[1]
    df[timestamp_column] = pd.to_datetime(df[timestamp_column])
    static_features = None
    if target != cols[-1]:
        # target is not the last column, then there are static features being merged in
        target_index = cols.index(target)
        static_columns = cols[target_index + 1 :]
        static_features = df[[id_column] + static_columns].groupby([id_column], sort=False).head(1)
        static_features.set_index(id_column, inplace=True)
        df.drop(columns=static_columns, inplace=True)
    df = TimeSeriesDataFrame.from_data_frame(df, id_column=id_column, timestamp_column=timestamp_column)
    if static_features is not None:
        print(static_features)
        df.static_features = static_features
    return df


def prepare_data(data_file, predictor_type, predictor_init_args=None):
    if predictor_type == "timeseries":
        assert predictor_init_args is not None
        data = load_pd.load(data_file)
        data = prepare_timeseries_dataframe(data, predictor_init_args)
    else:
        data = TabularDataset(data_file)
    return data


if __name__ == "__main__":
    # Disable Autotune
    os.environ["MXNET_CUDNN_AUTOTUNE_DEFAULT"] = "0"

    # ------------------------------------------------------------ Args parsing
    print("Starting AG")
    parser = argparse.ArgumentParser()

    # Data, model, and output directories
    parser.add_argument("--output-data-dir", type=str, default=get_env_if_present("SM_OUTPUT_DATA_DIR"))
    parser.add_argument("--model-dir", type=str, default=get_env_if_present("SM_MODEL_DIR"))
    parser.add_argument("--n_gpus", type=str, default=get_env_if_present("SM_NUM_GPUS"))
    parser.add_argument("--train_dir", type=str, default=get_env_if_present("SM_CHANNEL_TRAIN"))
    parser.add_argument("--tune_dir", type=str, required=False, default=get_env_if_present("SM_CHANNEL_TUNE"))
    parser.add_argument(
        "--train_images", type=str, required=False, default=get_env_if_present("SM_CHANNEL_TRAIN_IMAGES")
    )
    parser.add_argument(
        "--tune_images", type=str, required=False, default=get_env_if_present("SM_CHANNEL_TUNE_IMAGES")
    )
    parser.add_argument("--ag_config", type=str, default=get_env_if_present("SM_CHANNEL_CONFIG"))
    parser.add_argument("--serving_script", type=str, default=get_env_if_present("SM_CHANNEL_SERVING"))

    args, _ = parser.parse_known_args()

    print(f"Args: {args}")

    # See SageMaker-specific environment variables: https://sagemaker.readthedocs.io/en/stable/overview.html#prepare-a-training-script
    os.makedirs(args.output_data_dir, mode=0o777, exist_ok=True)

    config_file = get_input_path(args.ag_config)
    with open(config_file) as f:
        config = yaml.safe_load(f)  # AutoGluon-specific config

    if args.n_gpus:
        config["num_gpus"] = int(args.n_gpus)

    print("Running training job with the config:")
    pprint(config)

    # ---------------------------------------------------------------- Training
    save_path = os.path.normpath(args.model_dir)
    predictor_type = config["predictor_type"]
    predictor_init_args = config["predictor_init_args"]
    predictor_init_args["path"] = save_path
    predictor_fit_args = config["predictor_fit_args"]
    valid_predictor_types = ["tabular", "multimodal", "timeseries"]
    assert (
        predictor_type in valid_predictor_types
    ), f"predictor_type {predictor_type} not supported. Valid options are {valid_predictor_types}"
    if predictor_type == "tabular":
        predictor_cls = TabularPredictor
        if "feature_meatadata" in predictor_fit_args:
            predictor_fit_args["feature_meatadata"] = FeatureMetadata(**predictor_fit_args["feature_meatadata"])
    elif predictor_type == "multimodal":
        from autogluon.multimodal import MultiModalPredictor

        predictor_cls = MultiModalPredictor
    elif predictor_type == "timeseries":
        from autogluon.timeseries import TimeSeriesPredictor, TimeSeriesDataFrame

        predictor_cls = TimeSeriesPredictor

    train_file = get_input_path(args.train_dir)
    training_data = prepare_data(train_file, predictor_type, predictor_init_args)

    if predictor_type == "tabular" and "image_column" in config:
        feature_metadata = predictor_fit_args.get("feature_metadata", None)
        if feature_metadata is None:
            feature_metadata = FeatureMetadata.from_df(training_data)
        feature_metadata = feature_metadata.add_special_types({config["image_column"]: ["image_path"]})
        predictor_fit_args["feature_metadata"] = feature_metadata

    tuning_data = None
    if args.tune_dir:
        tune_file = get_input_path(args.tune_dir)
        tuning_data = prepare_data(tune_file, predictor_type)

    if args.train_images:
        train_image_compressed_file = get_input_path(args.train_images)
        train_images_dir = "train_images"
        shutil.unpack_archive(train_image_compressed_file, train_images_dir)
        image_column = config["image_column"]
        training_data[image_column] = training_data[image_column].apply(
            lambda path: os.path.join(train_images_dir, path)
        )

    if args.tune_images:
        tune_image_compressed_file = get_input_path(args.tune_images)
        tune_images_dir = "tune_images"
        shutil.unpack_archive(tune_image_compressed_file, tune_images_dir)
        image_column = config["image_column"]
        tuning_data[image_column] = tuning_data[image_column].apply(lambda path: os.path.join(tune_images_dir, path))

    predictor = predictor_cls(**predictor_init_args).fit(training_data, tuning_data=tuning_data, **predictor_fit_args)

    # When use automm backend, predictor needs to be saved with standalone flag to avoid need of internet access when loading
    # This is required because of https://discuss.huggingface.co/t/error-403-when-downloading-model-for-sagemaker-batch-inference/12571/6
    if predictor_type == "multimodal":
        predictor.save(path=save_path, standalone=True)

    if predictor_cls == TabularPredictor:
        if config.get("leaderboard", False):
            lb = predictor.leaderboard(silent=False)
            lb.to_csv(f"{args.output_data_dir}/leaderboard.csv")

    print("Saving serving script")
    serving_script_saving_path = os.path.join(save_path, "code")
    os.mkdir(serving_script_saving_path)
    serving_script_path = get_input_path(args.serving_script)
    shutil.move(serving_script_path, os.path.join(serving_script_saving_path, os.path.basename(serving_script_path)))
