[app]
title = 简易记账
package.name = jizhang
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.3
requirements = python3,kivy==2.2.1
orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
p4a.ignore_recipes = libthorvg

[buildozer]
log_level = 2
warn_on_root = 1
