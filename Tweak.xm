#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // دۆزینەوەی ڕێڕەوی فۆڵدەری سەرەکی ئەپەکە لەناو باینەرییەکەوە
        NSString *exePath = [[NSBundle mainBundle] executablePath];
        NSString *appDir = [exePath stringByDeletingLastPathComponent];
        
        // ناوی ئەو دایلبەی کە لەناو ئەپەکەدا هەیە (وەک لە وێنەکەدا دەردەکەوێت)
        NSString *targetDylib = @"libCoreSecurity.dylib";
        NSString *dylibPath = [appDir stringByAppendingPathComponent:targetDylib];
        
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        // پشکنین: ئەگەر کەسێک فایلەکەی لەناو ESign سڕییەوە، یارییەکە بکراشێنە
        // بەڵام ئەگەر فایلەکە لەوێ هەبوو، یارییەکە زۆر بە ئاسایی و بێ کێشە کرایەوە دەبێت
        if (![fileManager fileExistsAtPath:dylibPath]) {
            abort();
        }
    }
}
