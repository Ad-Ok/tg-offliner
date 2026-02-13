"""
Shared state for import progress and stop control.
Used by telegram_export.py (writer) and api/downloads.py (reader/writer).
Replaces HTTP-based communication between import thread and Flask API.
"""
import threading
import time

_state = {}
_lock = threading.Lock()


def set_status(channel_id, status, details=None):
    """Sets download status for a channel."""
    with _lock:
        _state[channel_id] = {
            'status': status,
            'details': details or {},
            'timestamp': time.time()
        }


def get_status(channel_id):
    """Gets download status for a channel."""
    with _lock:
        entry = _state.get(channel_id)
        return dict(entry) if entry else None


def get_all_statuses():
    """Gets all download statuses."""
    with _lock:
        return {k: dict(v) for k, v in _state.items()}


def update_progress(channel_id, posts_processed=0, total_posts=0, comments_processed=0):
    """Updates import progress for a channel."""
    with _lock:
        if channel_id in _state:
            _state[channel_id]['details'].update({
                'posts_processed': posts_processed,
                'total_posts': total_posts,
                'comments_processed': comments_processed
            })


def should_stop(channel_id):
    """Checks if import should be stopped."""
    with _lock:
        entry = _state.get(channel_id)
        return entry is not None and entry.get('status') == 'stopped'


def clear_status(channel_id):
    """Clears download status for a channel. Returns True if existed."""
    with _lock:
        if channel_id in _state:
            del _state[channel_id]
            return True
        return False
