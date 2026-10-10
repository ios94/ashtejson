#import <Foundation/Foundation.h>

%ctor {
    @autoreleasepool {
        NSString *targetDylib = @"AlertAshte.dylib";
        NSString *path = [NSString stringWithFormat:@"/Library/MobileSubstrate/DynamicLibraries/%@", targetDylib];
        NSFileManager *fileManager = [NSFileManager defaultManager];
        
        if (![fileManager fileExistsAtPath:path]) {
            abort();
        }
    }
}
