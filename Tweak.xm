#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // سیستەمی iOS خۆی یارییەکە دەشکێنێت ئەگەر دایلبەکە سڕابێتەوە!
        NSLog(@"-ashtemobile- Security Dylib Loaded!");
    }
}
