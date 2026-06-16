[app]

# (str) Title of your application
title = Secure Browser Ultimate

# (str) Package name
package.name = securebrowser

# (str) Package domain (needed for android/ios packaging)
package.domain = org.securebrowser

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (list) List of inclusions using pattern matching
# source.include_patterns = assets/*,images/*.png

# (list) List of exclusions using pattern matching
source.exclude_patterns = venv/*,build_env/*,build_venv/*,build_tool_venv/*,*.pyc,*/__pycache__/*,.buildozer/*,tor_data/*,bin/*

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,requests,urllib3,charset_normalizer,idna,pyjnius

# (str) Custom source folders for requirements
# 1. We need the AndroidX Webkit library for ProxyController
# 2. We need to bundle the Tor binary in the assets
android.gradle_dependencies = androidx.webkit:webkit:1.9.0

# (list) Permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.extra_manifest_application_arguments = %(source.dir)s/manifest_application_arguments.xml

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

# (str) Android entry point, default is to use PythonActivity
android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, default is ok for Kivy
android.apptheme = @android:style/Theme.NoTitleBar

# (list) Pattern to whitelist for the libpython.so
#android.whitelist =

# (str) Path to a custom whitelist file
#android.whitelist_src =

# (str) Path to a custom blacklist file
#android.blacklist_src =

# (list) List of Java .jar files to add to the libs so that pyjnius can access
# their classes. Don't add jar files that are already used by the build system.
# android.add_jars = foo.jar,bar.jar,path/to/baz.jar

# (list) List of Java files to add to the android project (can be java or a
# directory containing the files)
# android.add_src =

# (list) Android AAR archives to add
# android.add_aars =

# (list) Gradle repositories to add {can be listed as src or [repo_name]:[repo_url]}
# android.gradle_repositories =

# (list) packaging options to add 
# android.packaging_options = 

# (list) Java classes to add as activities to the manifest.
# android.add_activities = com.example.ExampleActivity

# (str) OUTrun mode (debug, release, or custom)
# android.release_mode = debug

# (list) Android architectures to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup
android.allow_backup = True

# (str) The Android SDK directory to use. Default to current user directory.
# android.sdk_path = 

# (str) The Android NDK directory to use. Default to current user directory.
# android.ndk_path = 

# (int) Android API to use. Default is 33
android.api = 34

# (int) Minimum API your APK will support. Default is 21
android.minapi = 21

# (int) Android SDK build-tools version to use. Default is 33.0.0
android.build_tools_version = 34.0.0

# (bool) If True, then skip trying to update the Android sdk
# android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (str) Android logcat filters to use
# android.logcat_filters = *:S python:D

# (str) Android additional libraries to copy into libs/armeabi
# android.add_libs_armeabi = lib/armeabi/libfoo.so:libs/armeabi/libfoo.so

# (str) Android additional libraries to copy into libs/arm64-v8a
# android.add_libs_arm64_v8a = lib/arm64-v8a/libfoo.so:libs/arm64-v8a/libfoo.so

# (str) Android additional libraries to copy into libs/x86
# android.add_libs_x86 = lib/x86/libfoo.so:libs/x86/libfoo.so

# (str) Android additional libraries to copy into libs/x86_64
# android.add_libs_x86_64 = lib/x86_64/libfoo.so:libs/x86_64/libfoo.so

# (list) The Android whitelist
# android.whitelist =

# (bool) If True, the app will be built as a bundle (aab) instead of an apk.
# android.build_as_aab = False

# (list) List of Java classes to add as services to the manifest.
# android.add_services =

# (str) Android additional Java classes to add to the project.
# android.add_java_src = 

# (str) Android additional res folders to add to the project.
# android.add_resources = 

# (str) Android additional manifest.xml files to add to the project.
# android.add_manifest = 

# (str) Android additional compile-time dependencies to add to the project.
# android.add_compile_dependencies = 

# (str) Android additional runtime dependencies to add to the project.
# android.add_runtime_dependencies = 

# (str) Android additional build-time dependencies to add to the project.
# android.add_build_dependencies = 

# (str) Android additional proguard configurations to add to the project.
# android.add_proguard_configs = 

# (str) Android additional assets to add to the project.
# android.add_assets = tor:tor

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = off, 1 = on)
warn_on_root = 1
