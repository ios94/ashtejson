#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // ڕێڕەوی فۆڵدەری سەرەکی ئەپەکە
        NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
        
        // دەبێت ئەم ناوە هەمان ئەو ناوە بێت کە لە inject.py دا دابنراوە (libCoreSecurity.dylib)
        NSString *targetDylib = @"libCoreSecurity.dylib";
        NSString *dylibPath = [bundlePath stringByAppendingPathComponent:targetDylib];
        
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        // ئەگەر فایلەکە هەبوو، یارییەکە بە بێ کێشە کار دەکات
        // تەنها ئەگەر کەسێک فایلەکەی سڕییەوە، یارییەکە دەشکێت (abort)
        if (![fileManager fileExistsAtPath:dylibPath]) {
            abort();
        }
    }
}
