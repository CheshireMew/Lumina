"""
Resource Limiter.
Provides cross-platform resource limits for sandboxed plugin processes.

Dual-Track Implementation:
- Linux: Uses `resource` module (setrlimit)
- Windows: Uses Job Objects API (pywin32)
"""

import sys
import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("ResourceLimiter")


@dataclass
class ResourceLimits:
    """Configuration for resource limits."""
    max_memory_mb: int = 512        # Maximum memory in MB
    max_cpu_seconds: int = 60       # Maximum CPU time in seconds
    max_processes: int = 5          # Maximum child processes
    max_open_files: int = 256       # Maximum open file descriptors
    
    def __post_init__(self):
        # Validate limits
        if self.max_memory_mb < 32:
            self.max_memory_mb = 32
        if self.max_cpu_seconds < 1:
            self.max_cpu_seconds = 1


class ResourceLimiter:
    """
    Cross-platform resource limiter for plugin sandboxing.
    
    Usage:
        limiter = ResourceLimiter()
        limiter.apply_limits(ResourceLimits(max_memory_mb=256))
        
    For subprocess usage:
        # In parent process, before fork/spawn
        limiter.setup_for_subprocess(process)
    """
    
    def __init__(self):
        self._platform = sys.platform
        self._job_handle = None  # Windows Job Object handle
        
    @property
    def is_windows(self) -> bool:
        return self._platform == "win32"
    
    @property
    def is_linux(self) -> bool:
        return self._platform.startswith("linux")
    
    @property
    def is_supported(self) -> bool:
        return self.is_windows or self.is_linux
    
    def apply_limits(self, limits: ResourceLimits) -> bool:
        """
        Apply resource limits to the current process.
        Should be called early in the sandboxed process lifecycle.
        
        Returns:
            True if limits were applied, False otherwise
        """
        if self.is_linux:
            return self._apply_linux_limits(limits)
        elif self.is_windows:
            return self._apply_windows_limits_current_process(limits)
        else:
            logger.warning(f"Resource limits not supported on {self._platform}")
            return False
    
    # ================================================================
    # Linux Implementation
    # ================================================================
    
    def _apply_linux_limits(self, limits: ResourceLimits) -> bool:
        """Apply limits using Python's resource module (Linux/Unix)."""
        try:
            import resource
            
            # Memory limit (virtual memory)
            mem_bytes = limits.max_memory_mb * 1024 * 1024
            try:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
                logger.debug(f"Set RLIMIT_AS to {limits.max_memory_mb}MB")
            except (ValueError, resource.error) as e:
                logger.warning(f"Failed to set memory limit: {e}")
            
            # CPU time limit
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (limits.max_cpu_seconds, limits.max_cpu_seconds))
                logger.debug(f"Set RLIMIT_CPU to {limits.max_cpu_seconds}s")
            except (ValueError, resource.error) as e:
                logger.warning(f"Failed to set CPU limit: {e}")
            
            # Max processes (fork bomb prevention)
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (limits.max_processes, limits.max_processes))
                logger.debug(f"Set RLIMIT_NPROC to {limits.max_processes}")
            except (ValueError, resource.error) as e:
                logger.warning(f"Failed to set process limit: {e}")
            
            # Max open files
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (limits.max_open_files, limits.max_open_files))
                logger.debug(f"Set RLIMIT_NOFILE to {limits.max_open_files}")
            except (ValueError, resource.error) as e:
                logger.warning(f"Failed to set file limit: {e}")
            
            logger.info(f"✅ Linux resource limits applied: {limits.max_memory_mb}MB, {limits.max_cpu_seconds}s CPU")
            return True
            
        except ImportError:
            logger.error("resource module not available on this platform")
            return False
        except Exception as e:
            logger.error(f"Failed to apply Linux limits: {e}")
            return False
    
    # ================================================================
    # Windows Implementation
    # ================================================================
    
    def _apply_windows_limits_current_process(self, limits: ResourceLimits) -> bool:
        """Apply limits to current process using Windows Job Objects."""
        try:
            import win32job
            import win32api
            import win32process
            import win32con
            
            # Create a Job Object
            job_name = f"LuminaSandbox_{os.getpid()}"
            job = win32job.CreateJobObject(None, job_name)
            
            # Configure limits
            info = win32job.QueryInformationJobObject(
                job, 
                win32job.JobObjectExtendedLimitInformation
            )
            
            # Set flags for what we want to limit
            limit_flags = 0
            
            # Memory limit
            if limits.max_memory_mb > 0:
                info['ProcessMemoryLimit'] = limits.max_memory_mb * 1024 * 1024
                info['JobMemoryLimit'] = limits.max_memory_mb * 1024 * 1024
                limit_flags |= win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
                limit_flags |= win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
            
            # CPU time limit (in 100-nanosecond units)
            if limits.max_cpu_seconds > 0:
                info['BasicLimitInformation']['PerProcessUserTimeLimit'] = limits.max_cpu_seconds * 10_000_000
                limit_flags |= win32job.JOB_OBJECT_LIMIT_PROCESS_TIME
            
            # Process count limit
            if limits.max_processes > 0:
                info['BasicLimitInformation']['ActiveProcessLimit'] = limits.max_processes
                limit_flags |= win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            
            info['BasicLimitInformation']['LimitFlags'] = limit_flags
            
            # Apply the configuration
            win32job.SetInformationJobObject(
                job,
                win32job.JobObjectExtendedLimitInformation,
                info
            )
            
            # Assign current process to job
            current_process = win32api.GetCurrentProcess()
            win32job.AssignProcessToJobObject(job, current_process)
            
            self._job_handle = job
            
            logger.info(f"✅ Windows resource limits applied: {limits.max_memory_mb}MB, {limits.max_cpu_seconds}s CPU")
            return True
            
        except ImportError:
            logger.error("pywin32 not installed. Run: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"Failed to apply Windows limits: {e}", exc_info=True)
            return False
    
    def create_job_for_subprocess(self, limits: ResourceLimits) -> Optional[object]:
        """
        Create a Job Object that can be used for a subprocess.
        Returns the job handle that should be used with subprocess creation.
        
        Usage:
            job = limiter.create_job_for_subprocess(limits)
            proc = subprocess.Popen(...)
            limiter.assign_process_to_job(job, proc.pid)
        """
        if not self.is_windows:
            return None
        
        try:
            import win32job
            
            job_name = f"LuminaSandbox_Child_{os.getpid()}"
            job = win32job.CreateJobObject(None, job_name)
            
            info = win32job.QueryInformationJobObject(
                job,
                win32job.JobObjectExtendedLimitInformation
            )
            
            limit_flags = 0
            
            if limits.max_memory_mb > 0:
                info['ProcessMemoryLimit'] = limits.max_memory_mb * 1024 * 1024
                limit_flags |= win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
            
            if limits.max_cpu_seconds > 0:
                info['BasicLimitInformation']['PerProcessUserTimeLimit'] = limits.max_cpu_seconds * 10_000_000
                limit_flags |= win32job.JOB_OBJECT_LIMIT_PROCESS_TIME
            
            if limits.max_processes > 0:
                info['BasicLimitInformation']['ActiveProcessLimit'] = limits.max_processes
                limit_flags |= win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            
            # Kill child processes when job terminates
            limit_flags |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            
            info['BasicLimitInformation']['LimitFlags'] = limit_flags
            
            win32job.SetInformationJobObject(
                job,
                win32job.JobObjectExtendedLimitInformation,
                info
            )
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to create job object: {e}")
            return None
    
    def assign_process_to_job(self, job: object, pid: int) -> bool:
        """Assign a process to a Job Object by PID."""
        if not self.is_windows or job is None:
            return False
        
        try:
            import win32api
            import win32job
            import win32con
            
            # Open the process
            handle = win32api.OpenProcess(
                win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE,
                False,
                pid
            )
            
            # Assign to job
            win32job.AssignProcessToJobObject(job, handle)
            win32api.CloseHandle(handle)
            
            logger.debug(f"Assigned process {pid} to job object")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign process to job: {e}")
            return False
    
    def cleanup(self):
        """Clean up any held resources."""
        if self._job_handle is not None:
            try:
                import win32api
                win32api.CloseHandle(self._job_handle)
            except Exception:
                pass
            self._job_handle = None


# Convenience function for subprocess pre-exec
def apply_sandbox_limits(limits: ResourceLimits = None):
    """
    Apply sandbox limits to current process.
    Designed to be called as preexec_fn in subprocess.Popen (Linux)
    or via Job Objects (Windows).
    
    Usage (Linux):
        subprocess.Popen(..., preexec_fn=lambda: apply_sandbox_limits())
    """
    limits = limits or ResourceLimits()
    limiter = ResourceLimiter()
    limiter.apply_limits(limits)
