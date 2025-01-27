from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from ..endpoint.endpoint import Endpoint


class Backend(ABC):
    name = "backend"

    def __init__(self, **kwargs) -> None:
        self.initialize(**kwargs)

    @abstractmethod
    def initialize(self, **kwargs) -> None:
        """Initialize the backend."""
        raise NotImplementedError

    @abstractmethod
    def generate_default_permission(self, **kwargs) -> Dict[str, str]:
        """Generate default permission file user could use to setup the corresponding entity, i.e. IAM Role in AWS"""
        raise NotImplementedError

    @abstractmethod
    def parse_backend_fit_kwargs(self, kwargs: Dict) -> Dict[str, Any]:
        """Parse backend specific kwargs and get them ready to be sent to fit call"""
        raise NotImplementedError

    @abstractmethod
    def attach_job(self, job_name: str) -> None:
        """
        Attach to a existing training job.
        This is useful when the local process crashed and you want to reattach to the previous job

        Parameters
        ----------
        job_name: str
            The name of the job being attached
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_fit(self) -> bool:
        """Whether the backend is fitted"""
        raise NotImplementedError

    @abstractmethod
    def get_fit_job_status(self) -> str:
        """
        Get the status of the training job.
        This is useful when the user made an asynchronous call to the `fit()` function
        """
        raise NotImplementedError

    @abstractmethod
    def get_fit_job_output_path(self) -> str:
        """Get the output path in the cloud of the trained artifact"""
        raise NotImplementedError

    @abstractmethod
    def get_fit_job_info(self) -> Dict[str, Any]:
        """
        Get general info of the training job.
        """
        raise NotImplementedError

    @abstractmethod
    def fit(self, **kwargs) -> None:
        """Fit AG on the backend"""
        raise NotImplementedError

    @abstractmethod
    def parse_backend_deploy_kwargs(self, kwargs: Dict) -> Dict[str, Any]:
        """Parse backend specific kwargs and get them ready to be sent to deploy call"""
        raise NotImplementedError

    @abstractmethod
    def deploy(self, **kwargs) -> None:
        """Deploy and endpoint"""
        raise NotImplementedError

    @abstractmethod
    def cleanup_deployment(self, **kwargs) -> None:
        """Delete endpoint, and cleanup other artifacts"""
        raise NotImplementedError

    @abstractmethod
    def attach_endpoint(self, endpoint: Endpoint) -> None:
        """Attach the backend to an existing endpoint"""
        raise NotImplementedError

    @abstractmethod
    def detach_endpoint(self) -> Endpoint:
        """Detach the current endpoint and return it"""
        raise NotImplementedError

    @abstractmethod
    def predict_real_time(self, test_data: Union[str, pd.DataFrame], **kwargs) -> Union[pd.DataFrame, pd.Series]:
        """Realtime prediction with the endpoint"""
        raise NotImplementedError

    @abstractmethod
    def predict_proba_real_time(self, test_data: Union[str, pd.DataFrame], **kwargs) -> Union[pd.DataFrame, pd.Series]:
        """Realtime prediction probability with the endpoint"""
        raise NotImplementedError

    @abstractmethod
    def parse_backend_predict_kwargs(self, kwargs: Dict) -> Dict[str, Any]:
        """Parse backend specific kwargs and get them ready to be sent to predict call"""
        raise NotImplementedError

    @abstractmethod
    def get_batch_inference_job_info(self, job_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get general info of the batch inference job.
        If job_name not specified, return the info of the most recent batch inference job
        """
        raise NotImplementedError

    @abstractmethod
    def get_batch_inference_job_status(self, job_name: Optional[str] = None) -> str:
        """
        Get general status of the batch inference job.
        If job_name not specified, return the info of the most recent batch inference job
        """
        raise NotImplementedError

    @abstractmethod
    def get_batch_inference_jobs(self) -> List[str]:
        """Get a list of names of all batch inference jobs"""
        raise NotImplementedError

    @abstractmethod
    def predict(self, test_data: Union[str, pd.DataFrame], **kwargs) -> Union[pd.DataFrame, pd.Series]:
        """Batch inference"""
        raise NotImplementedError

    @abstractmethod
    def predict_proba(self, test_data: Union[str, pd.DataFrame], **kwargs) -> Union[pd.DataFrame, pd.Series]:
        """Batch inference probability"""
        raise NotImplementedError
