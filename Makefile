TARGET := iphone:clang:latest:13.0
ARCHS = arm64
DEBUG = 0
FINALPACKAGE = 1

TWEAK_NAME = AlertAshte

AlertAshte_FILES = Tweak.xm
AlertAshte_FRAMEWORKS = UIKit
AlertAshte_CFLAGS = -fobjc-arc

include $(THEOS)/makefiles/common.mk
include $(THEOS_MAKE_PATH)/tweak.mk
