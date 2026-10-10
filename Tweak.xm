#import <Foundation/Foundation.h>
#import <dlfcn.h>

%ctor {
    @autoreleasepool {
        NSString *targetDylib = @"AlertAshte.dylib";
        NSString *path = [NSString stringWithFormat:@"/Library/MobileSubstrate/DynamicLibraries/%@", targetDylib];
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        // پشکنینی بوونی فایل
        if (![fileManager fileExistsAtPath:path]) {
            abort();
        }
        
        // پشکنینی شیاوی بارکردن بۆ ڕێگری لە لادانی پاراستن
        void *handle = dlopen([path UTF8String], RTLD_LAZY);
        if (!handle) {
            abort();
        } else {
            dlclose(handle);
        }
    }
}
