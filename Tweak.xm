#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
        NSString *targetDylib = @"libCoreSecurity.dylib";
        NSString *dylibPath = [bundlePath stringByAppendingPathComponent:targetDylib];
        
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        if (![fileManager fileExistsAtPath:dylibPath]) {
            abort();
        }
    }
}
