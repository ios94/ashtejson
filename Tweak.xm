#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // پشکنینی نەرم و پارێزراو بۆ دڵنیابوون لە کارکردنی یارییەکە
        NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
        NSString *targetDylib = @"libCoreSecurity.dylib";
        NSString *dylibPath = [bundlePath stringByAppendingPathComponent:targetDylib];
        NSString *frameworksPath = [bundlePath stringByAppendingPathComponent:@"Frameworks/libCoreSecurity.dylib"];
        
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        // ئەگەر لە هیچ کدام لەو دوو شوێنەدا نەبوو، ئینجا با کراش بکات
        if (![fileManager fileExistsAtPath:dylibPath] && ![fileManager fileExistsAtPath:frameworksPath]) {
            // بۆ تاقیکردنەوە دەتوانیت ئەمە فعال بکەیت یان لێیگەڕێیت
            // abort();
        }
    }
}
