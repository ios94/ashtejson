#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // دۆزینەوەی ڕێڕەوی ڕەقی فۆڵدەری ئەپەکە بە شێوازێکی فەرمی
        NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
        NSString *targetDylib = @"libCoreSecurity.dylib";
        NSString *dylibPath = [bundlePath stringByAppendingPathComponent:targetDylib];
        
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        // پشکنین: تەنها و تەنها ئەگەر کەسێک فایلەکەی بە تەواوی سڕییەوە، یارییەکە بکراشێنە
        if (![fileManager fileExistsAtPath:dylibPath]) {
            abort();
        }
    }
}
