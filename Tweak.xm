#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // دۆزینەوەی ڕێڕەوی فۆڵدەری سەرەکی ئەپەکە
        NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
        
        // ناوی ఆ فایلی دایلبەی کە لەناو ئەپەکەدا دانراوە
        NSString *targetDylib = @"libCoreSecurity.dylib";
        NSString *dylibPath = [bundlePath stringByAppendingPathComponent:targetDylib];
        
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        // پشکنینی پاراستن:
        // ئەگەر فایلەکە لە شوێنی خۆیدا هەبوو -> یارییەکە بێ کێشە کرایەوە دەبێت و کار دەکات.
        // ئەگەر کەسێک فایلەکەی لەناو ESign سڕییەوە -> فەرمانی abort جێبەجێ دەبێت و یارییەکە یەکسەر دەشکێت!
        if (![fileManager fileExistsAtPath:dylibPath]) {
            abort();
        }
    }
}
