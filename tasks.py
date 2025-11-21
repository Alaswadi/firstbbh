"""
Celery tasks for bug bounty automation.
All scanning operations are executed asynchronously via Celery workers.
"""
from celery import Task
from celery_app import celery_app
from celery.utils.log import get_task_logger
import os
from datetime import datetime

# Import scanning modules
from main import run_scan as run_scan_sync
from config import OUTPUT_DIR
from database import (
    init_db,
    update_scan_status,
    get_scan,
    create_scan as db_create_scan
)

logger = get_task_logger(__name__)


class CallbackTask(Task):
    """Base task with callbacks for state changes."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed with error: {exc}")
        # Update scan status if scan_id is available
        if args and len(args) > 0:
            try:
                # Try to extract scan_id from args
                scan_id = kwargs.get('scan_id') or (args[2] if len(args) > 2 else None)
                if scan_id:
                    update_scan_status(scan_id, 'Failed', str(exc))
            except Exception as e:
                logger.error(f"Failed to update scan status: {e}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"Task {task_id} is being retried due to: {exc}")


@celery_app.task(bind=True, base=CallbackTask, name='tasks.scan_domain_task')
def scan_domain_task(self, domain, scan_type="full", tools=None, scan_id=None):
    """
    Main task for scanning a domain.
    
    Args:
        domain: Target domain to scan
        scan_type: Type of scan (full, subdomain, probing)
        tools: List of tools to use
        scan_id: Existing scan ID or None to create new
    
    Returns:
        dict: Scan results with statistics
    """
    logger.info(f"Starting scan for domain: {domain}")
    
    # Update task state to STARTED
    self.update_state(
        state='STARTED',
        meta={'domain': domain, 'status': 'Initializing scan...'}
    )
    
    try:
        # Initialize database if needed
        init_db()
        
        # Create scan record if not provided
        if scan_id is None:
            scan_id = db_create_scan(domain, scan_type, tools)
            logger.info(f"Created scan record with ID: {scan_id}")
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'domain': domain,
                'scan_id': scan_id,
                'status': 'Running subdomain discovery...',
                'progress': 10
            }
        )
        
        # Run the actual scan (synchronous function)
        result = run_scan_sync(domain, scan_type, tools, scan_id)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'domain': domain,
                'scan_id': scan_id,
                'status': 'Scan completed successfully',
                'progress': 100
            }
        )
        
        logger.info(f"Scan completed for domain: {domain}")
        
        return {
            'status': 'success',
            'scan_id': scan_id,
            'domain': domain,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Scan failed for domain {domain}: {str(e)}")
        if scan_id:
            update_scan_status(scan_id, 'Failed', str(e))
        raise


@celery_app.task(bind=True, base=CallbackTask, name='tasks.run_subdomain_discovery_task')
def run_subdomain_discovery_task(self, domain, output_dir, tools=None):
    """
    Task for subdomain discovery.
    
    Args:
        domain: Target domain
        output_dir: Output directory for results
        tools: List of discovery tools to use
    
    Returns:
        list: Discovered subdomains
    """
    from modules.discovery import run_discovery
    
    logger.info(f"Running subdomain discovery for: {domain}")
    
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Discovering subdomains...', 'progress': 0}
    )
    
    try:
        subdomains = run_discovery(domain, output_dir, tools or ['subfinder'])
        
        logger.info(f"Found {len(subdomains)} subdomains for {domain}")
        
        return {
            'status': 'success',
            'subdomains': subdomains,
            'count': len(subdomains)
        }
    except Exception as e:
        logger.error(f"Subdomain discovery failed: {str(e)}")
        raise


@celery_app.task(bind=True, base=CallbackTask, name='tasks.run_port_scan_task')
def run_port_scan_task(self, hosts, output_file):
    """
    Task for port scanning.
    
    Args:
        hosts: List of hosts or file path
        output_file: Output file path
    
    Returns:
        list: Open ports found
    """
    from modules.probing import run_naabu
    
    logger.info(f"Running port scan on hosts")
    
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Scanning ports...', 'progress': 0}
    )
    
    try:
        # If hosts is a list, write to temp file
        if isinstance(hosts, list):
            temp_input = output_file.replace('.txt', '_input.txt')
            with open(temp_input, 'w') as f:
                for host in hosts:
                    f.write(f"{host}\n")
            hosts = temp_input
        
        open_ports = run_naabu(hosts, output_file)
        
        logger.info(f"Found {len(open_ports)} open ports")
        
        return {
            'status': 'success',
            'open_ports': open_ports,
            'count': len(open_ports)
        }
    except Exception as e:
        logger.error(f"Port scan failed: {str(e)}")
        raise


@celery_app.task(bind=True, base=CallbackTask, name='tasks.run_web_probing_task')
def run_web_probing_task(self, subdomains, output_file):
    """
    Task for web server probing with HTTPX.
    
    Args:
        subdomains: List of subdomains to probe
        output_file: Output file path
    
    Returns:
        list: Live hosts with details
    """
    from modules.probing import run_httpx_batch
    
    logger.info(f"Probing {len(subdomains)} subdomains for web servers")
    
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Probing web servers...', 'progress': 0}
    )
    
    try:
        live_hosts = run_httpx_batch(subdomains, output_file)
        
        logger.info(f"Found {len(live_hosts)} live web servers")
        
        return {
            'status': 'success',
            'live_hosts': live_hosts,
            'count': len(live_hosts)
        }
    except Exception as e:
        logger.error(f"Web probing failed: {str(e)}")
        raise


@celery_app.task(bind=True, base=CallbackTask, name='tasks.run_content_discovery_task')
def run_content_discovery_task(self, hosts, output_dir):
    """
    Task for content discovery with GAU.
    
    Args:
        hosts: List of hosts
        output_dir: Output directory
    
    Returns:
        list: Discovered URLs
    """
    from modules.content import run_gau_parallel
    
    logger.info(f"Running content discovery on {len(hosts)} hosts")
    
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Discovering content...', 'progress': 0}
    )
    
    try:
        urls = run_gau_parallel(hosts, output_dir)
        
        logger.info(f"Found {len(urls)} URLs")
        
        return {
            'status': 'success',
            'urls': urls,
            'count': len(urls)
        }
    except Exception as e:
        logger.error(f"Content discovery failed: {str(e)}")
        raise


@celery_app.task(name='tasks.cleanup_old_scans')
def cleanup_old_scans(days=30):
    """
    Periodic task to cleanup old scan data.
    
    Args:
        days: Number of days to keep scans
    """
    from database import get_all_scans, delete_scan
    from datetime import timedelta
    
    logger.info(f"Cleaning up scans older than {days} days")
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        scans = get_all_scans(limit=1000)
        
        deleted_count = 0
        for scan in scans:
            scan_date = datetime.fromisoformat(scan['start_time'])
            if scan_date < cutoff_date:
                delete_scan(scan['id'])
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old scans")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise


@celery_app.task(bind=True, name='tasks.get_task_status')
def get_task_status(self, task_id):
    """
    Get the status of a task.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        dict: Task status information
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        'task_id': task_id,
        'state': result.state,
        'info': result.info,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'failed': result.failed() if result.ready() else None,
    }
