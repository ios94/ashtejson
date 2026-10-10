#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        // هیچ پشکنینێک لێرە پێویست نییە، سیستەمی iOS خۆی یارییەکە دەشکێنێت ئەگەر دایلبەکە سڕابێتەوە!
        NSLog(@"-ashtemobile- Security Dylib Loaded!");
    }
}
