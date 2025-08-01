##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2025, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""A blueprint module providing utility functions for the application."""

from pgadmin.utils import driver
from flask import request, current_app
from flask_babel import gettext
from pgadmin.user_login_check import pga_login_required
from pathlib import Path
from pgadmin.utils import PgAdminModule, get_binary_path_versions
from pgadmin.utils.constants import PREF_LABEL_USER_INTERFACE, \
    PREF_LABEL_FILE_DOWNLOADS
from pgadmin.utils.csrf import pgCSRFProtect
from pgadmin.utils.session import cleanup_session_files
from pgadmin.misc.themes import get_all_themes
from pgadmin.utils.ajax import precondition_required, make_json_response, \
    internal_server_error, make_response
from pgadmin.utils.heartbeat import log_server_heartbeat, \
    get_server_heartbeat, stop_server_heartbeat
import config
import threading
import time
import json
import os
import sys
import ssl
from urllib.request import urlopen
from urllib.parse import unquote
from pgadmin.settings import get_setting, store_setting

MODULE_NAME = 'misc'


class MiscModule(PgAdminModule):
    LABEL = gettext('Miscellaneous')

    def register_preferences(self):
        """
        Register preferences for this module.
        """
        lang_options = []
        for lang in config.LANGUAGES:
            lang_options.append(
                {
                    'label': config.LANGUAGES[lang],
                    'value': lang
                }
            )

        # Register options for the User language settings
        self.preference.register(
            'user_interface', 'user_language',
            gettext("Language"), 'options', 'en',
            category_label=PREF_LABEL_USER_INTERFACE,
            options=lang_options,
            control_props={
                'allowClear': False,
            }
        )

        theme_options = []

        for theme, theme_data in (get_all_themes()).items():
            theme_options.append({
                'label': theme_data['disp_name']
                .replace('_', ' ')
                .replace('-', ' ')
                .title(),
                'value': theme,
                'preview_src': 'js/generated/img/' + theme_data['preview_img']
                if 'preview_img' in theme_data else None
            })

        self.preference.register(
            'user_interface', 'theme',
            gettext("Theme"), 'options', 'light',
            category_label=PREF_LABEL_USER_INTERFACE,
            options=theme_options,
            control_props={
                'allowClear': False,
                'creatable': False,
            },
            help_str=gettext(
                'Click the save button to apply the theme. Below is the '
                'preview of the theme.'
            )
        )
        self.preference.register(
            'user_interface', 'layout',
            gettext("Layout"), 'options', 'workspace',
            category_label=PREF_LABEL_USER_INTERFACE,
            options=[{'label': gettext('Classic'), 'value': 'classic'},
                     {'label': gettext('Workspace'), 'value': 'workspace'}],
            control_props={
                'allowClear': False,
                'creatable': False,
            },
            help_str=gettext(
                'Choose the layout that suits you best. pgAdmin offers two '
                'options: the Classic layout, a longstanding and familiar '
                'design, and the Workspace layout, which provides distraction '
                'free dedicated areas for the Query Tool, PSQL, and Schema '
                'Diff tools.'
            )
        )
        self.preference.register(
            'user_interface', 'open_in_res_workspace',
            gettext("Open the Query Tool/PSQL in their respective workspaces"),
            'boolean', False,
            category_label=PREF_LABEL_USER_INTERFACE,
            help_str=gettext(
                'This setting applies only when the layout is set to '
                'Workspace Layout. When set to True, all Query Tool/PSQL '
                'tabs will open in their respective workspaces. By default, '
                'this setting is False, meaning that Query Tool/PSQL tabs '
                'will open in the currently active workspace (either the '
                'default or the workspace selected at the time of opening)'
            )
        )

        self.preference.register(
            'user_interface', 'save_app_state',
            gettext("Save the application state?"),
            'boolean', True,
            category_label=PREF_LABEL_USER_INTERFACE,
            help_str=gettext(
                'If set to True, pgAdmin will save the state of opened tools'
                ' (such as Query Tool, PSQL, Schema Diff, and ERD), including'
                ' any unsaved data. This data will be automatically restored'
                ' in the event of an unexpected shutdown or browser refresh.'
            )
        )

        if not config.SERVER_MODE:
            self.preference.register(
                'file_downloads', 'automatically_open_downloaded_file',
                gettext("Automatically open downloaded file?"),
                'boolean', False,
                category_label=PREF_LABEL_FILE_DOWNLOADS,
                help_str=gettext(
                    '''This setting is applicable and visible only in
                    desktop mode. When set to True, the downloaded file
                    will automatically open in the system's default
                    application associated with that file type.'''
                )
            )
            self.preference.register(
                'file_downloads', 'prompt_for_download_location',
                gettext("Prompt for the download location?"),
                'boolean', True,
                category_label=PREF_LABEL_FILE_DOWNLOADS,
                help_str=gettext(
                    'This setting is applicable and visible only '
                    'in desktop mode. When set to True, a prompt '
                    'will appear after clicking the download button, '
                    'allowing you to choose the download location'
                )
            )

    def get_exposed_url_endpoints(self):
        """
        Returns:
            list: a list of url endpoints exposed to the client.
        """
        return ['misc.ping', 'misc.index', 'misc.cleanup',
                'misc.validate_binary_path', 'misc.log_heartbeat',
                'misc.stop_heartbeat', 'misc.get_heartbeat',
                'misc.upgrade_check', 'misc.auto_update']

    def register(self, app, options):
        """
        Override the default register function to automagically register
        sub-modules at once.
        """
        from .bgprocess import blueprint as module
        self.submodules.append(module)

        from .cloud import blueprint as module
        self.submodules.append(module)

        from .dependencies import blueprint as module
        self.submodules.append(module)

        from .dependents import blueprint as module
        self.submodules.append(module)

        from .file_manager import blueprint as module
        self.submodules.append(module)

        from .statistics import blueprint as module
        self.submodules.append(module)

        from .workspaces import blueprint as module
        self.submodules.append(module)

        def autovacuum_sessions():
            try:
                with app.app_context():
                    cleanup_session_files()
            finally:
                # repeat every five minutes until exit
                # https://github.com/python/cpython/issues/98230
                t = threading.Timer(5 * 60, autovacuum_sessions)
                t.daemon = True
                t.start()

        app.register_before_app_start(autovacuum_sessions)

        super().register(app, options)


# Initialise the module
blueprint = MiscModule(MODULE_NAME, __name__)


##########################################################################
# A special URL used to "ping" the server
##########################################################################
@blueprint.route("/", endpoint='index')
def index():
    return ''


##########################################################################
# A special URL used to "ping" the server
##########################################################################
@blueprint.route("/ping")
@pgCSRFProtect.exempt
def ping():
    """Generate a "PING" response to indicate that the server is alive."""
    return "PING"


# For Garbage Collecting closed connections
@blueprint.route("/cleanup", methods=['POST'])
@pgCSRFProtect.exempt
def cleanup():
    driver.ping()
    return ""


@blueprint.route("/heartbeat/log", methods=['POST'])
@pgCSRFProtect.exempt
def log_heartbeat():
    data = None
    if hasattr(request.data, 'decode'):
        data = request.data.decode('utf-8')

    if data != '':
        data = json.loads(data)

    status, msg = log_server_heartbeat(data)
    if status:
        return make_json_response(data=msg, status=200)
    else:
        return make_json_response(data=msg, status=404)


@blueprint.route("/heartbeat/stop", methods=['POST'])
@pgCSRFProtect.exempt
def stop_heartbeat():
    data = None
    if hasattr(request.data, 'decode'):
        data = request.data.decode('utf-8')

    if data != '':
        data = json.loads(data)

    _, msg = stop_server_heartbeat(data)
    return make_json_response(data=msg,
                              status=200)


@blueprint.route("/get_heartbeat/<int:sid>", methods=['GET'])
@pgCSRFProtect.exempt
def get_heartbeat(sid):
    heartbeat_data = get_server_heartbeat(sid)
    return make_json_response(data=heartbeat_data,
                              status=200)


##########################################################################
# A special URL used to shut down the server
##########################################################################
@blueprint.route("/shutdown", methods=('get', 'post'))
@pgCSRFProtect.exempt
def shutdown():
    if config.SERVER_MODE is not True:
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        return 'SHUTDOWN'
    else:
        return ''


##########################################################################
# A special URL used to validate the binary path
##########################################################################
@blueprint.route("/validate_binary_path",
                 endpoint="validate_binary_path",
                 methods=["POST"])
@pga_login_required
def validate_binary_path():
    """
    This function is used to validate the specified utilities path by
    running the utilities with their versions.
    """
    data = None
    if hasattr(request.data, 'decode'):
        data = request.data.decode('utf-8')

    if data != '':
        data = json.loads(data)

    version_str = ''

    # Do not allow storage dir as utility path
    if 'utility_path' in data and data['utility_path'] is not None and \
        Path(config.STORAGE_DIR) != Path(data['utility_path']) and \
            Path(config.STORAGE_DIR) not in Path(data['utility_path']).parents:
        binary_versions = get_binary_path_versions(data['utility_path'])
        for utility, version in binary_versions.items():
            if version is None:
                version_str += "<b>" + utility + ":</b> " + \
                               "not found on the specified binary path.<br/>"
            else:
                version_str += "<b>" + utility + ":</b> " + version + "<br/>"
    else:
        return precondition_required(gettext('Invalid binary path.'))

    return make_json_response(data=gettext(version_str), status=200)


@blueprint.route("/upgrade_check", endpoint="upgrade_check",
                 methods=['GET'])
@pga_login_required
def upgrade_check():
    """
    Check for application updates and return update metadata to the client.
    - Compares current version with remote version data.
    - Supports auto-update in desktop mode.
    """
    # Determine if this check was manually triggered by the user
    trigger_update_check = (request.args.get('trigger_update_check', 'false')
                            .lower() == 'true')

    platform = None
    ret = {"outdated": False}

    if config.UPGRADE_CHECK_ENABLED:
        last_check = get_setting('LastUpdateCheck', default='0')
        today = time.strftime('%Y%m%d')

        data = None
        url = '%s?version=%s' % (
            config.UPGRADE_CHECK_URL, config.APP_VERSION)
        current_app.logger.debug('Checking version data at: %s' % url)

        # Attempt to fetch upgrade data from remote URL
        try:
            # Do not wait for more than 5 seconds.
            # It stuck on rendering the browser.html, while working in the
            # broken network.
            if os.path.exists(config.CA_FILE) and sys.version_info >= (
                    3, 13):
                # Use SSL context for Python 3.13+
                context = ssl.create_default_context(cafile=config.CA_FILE)
                response = urlopen(url, data=data, timeout=5,
                                   context=context)
            elif os.path.exists(config.CA_FILE):
                # Use cafile parameter for older versions
                response = urlopen(url, data=data, timeout=5,
                                   cafile=config.CA_FILE)
            else:
                response = urlopen(url, data, 5)
            current_app.logger.debug(
                'Version check HTTP response code: %d' % response.getcode()
            )

            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                current_app.logger.debug('Response data: %s' % data)
        except Exception:
            current_app.logger.exception(
                'Exception when checking for update')
            return internal_server_error('Failed to check for update')

        if data:
            # Determine platform
            if sys.platform == 'darwin':
                platform = 'macos'
            elif sys.platform == 'win32':
                platform = 'windows'

            upgrade_version_int = data[config.UPGRADE_CHECK_KEY]['version_int']
            auto_update_url_exists = data[config.UPGRADE_CHECK_KEY][
                'auto_update_url'][platform] != ''

            # Construct common response dicts for auto-update support
            auto_update_common_res = {
                "check_for_auto_updates": True,
                "auto_update_url": data[config.UPGRADE_CHECK_KEY][
                    'auto_update_url'][platform],
                "platform": platform,
                "installer_type": config.UPGRADE_CHECK_KEY,
                "current_version": config.APP_VERSION,
                "upgrade_version": data[config.UPGRADE_CHECK_KEY]['version'],
                "current_version_int": config.APP_VERSION_INT,
                "upgrade_version_int": upgrade_version_int,
                "product_name": config.APP_NAME,
            }

            # Check for updates if the last check was before today(daily check)
            if int(last_check) < int(today):
                # App is outdated
                if upgrade_version_int > config.APP_VERSION_INT:
                    if not config.SERVER_MODE and auto_update_url_exists:
                        ret = {**auto_update_common_res, "outdated": True}
                    else:
                        # Auto-update unsupported
                        ret = {
                            "outdated": True,
                            "check_for_auto_updates": False,
                            "current_version": config.APP_VERSION,
                            "upgrade_version": data[config.UPGRADE_CHECK_KEY][
                                'version'],
                            "product_name": config.APP_NAME,
                            "download_url": data[config.UPGRADE_CHECK_KEY][
                                'download_url']
                        }
                # App is up-to-date, but auto-update should be enabled
                elif (upgrade_version_int == config.APP_VERSION_INT and
                        not config.SERVER_MODE and auto_update_url_exists):
                    ret = {**auto_update_common_res, "outdated": False}
            # If already checked today,
            # return auto-update info only if supported
            elif (int(last_check) == int(today) and
                    not config.SERVER_MODE and auto_update_url_exists):
                # Check for updates when triggered by user
                # and new version is available
                if (upgrade_version_int > config.APP_VERSION_INT and
                        trigger_update_check):
                    ret = {**auto_update_common_res, "outdated": True}
                else:
                    ret = {**auto_update_common_res, "outdated": False}

        store_setting('LastUpdateCheck', today)
    return make_json_response(data=ret)


@blueprint.route("/auto_update/<current_version_int>/<latest_version>"
                 "/<latest_version_int>/<product_name>/<path:ftp_url>/",
                 methods=['GET'])
@pgCSRFProtect.exempt
def auto_update(current_version_int, latest_version, latest_version_int,
                product_name, ftp_url):
    """
    Get auto-update information for the desktop app.

    Returns update metadata (download URL and version name)
    if a newer version is available. Responds with HTTP 204
    if the current version is up to date.
    """
    if latest_version_int > current_version_int:
        update_info = {
            'url': unquote(ftp_url),
            'name': f'{product_name} v{latest_version}',
        }
        current_app.logger.debug(update_info)
        return make_response(response=update_info, status=200)
    else:
        return make_response(status=204)
