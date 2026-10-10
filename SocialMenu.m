#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

@interface AshteWelcomeViewController : UIViewController
@property (nonatomic, strong) UIView *glassCard;
@property (nonatomic, strong) UIImageView *logoView; 
- (void)openTelegram;
- (void)openTikTok;
- (void)openWebsite;
- (void)closeTapped;
- (void)playHaptic;
- (void)loadAndCacheImage:(NSString *)urlStr forImageView:(UIImageView *)imgView placeholder:(NSString *)sysName;
- (UIButton *)createModernBlockButton:(NSString *)url placeholder:(NSString *)ph action:(SEL)action;
@end

@implementation AshteWelcomeViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    
    self.view.backgroundColor = [UIColor clearColor];
    self.modalPresentationStyle = UIModalPresentationOverFullScreen;

    UIBlurEffect *blurEffect = [UIBlurEffect effectWithStyle:UIBlurEffectStyleLight];
    UIVisualEffectView *blurView = [[UIVisualEffectView alloc] initWithEffect:blurEffect];
    blurView.frame = self.view.bounds;
    blurView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    [self.view addSubview:blurView];

    self.glassCard = [[UIView alloc] init];
    self.glassCard.backgroundColor = [UIColor colorWithWhite:1.0 alpha:0.9]; 
    self.glassCard.layer.cornerRadius = 24;
    self.glassCard.layer.borderWidth = 1.0;
    self.glassCard.layer.borderColor = [UIColor colorWithWhite:0.0 alpha:0.1].CGColor;
    
    self.glassCard.layer.shadowColor = [UIColor blackColor].CGColor;
    self.glassCard.layer.shadowOpacity = 0.12;
    self.glassCard.layer.shadowOffset = CGSizeMake(0, 10);
    self.glassCard.layer.shadowRadius = 25;
    
    self.glassCard.translatesAutoresizingMaskIntoConstraints = NO;
    self.glassCard.alpha = 0; 
    self.glassCard.transform = CGAffineTransformMakeScale(0.9, 0.9);
    
    [self.view addSubview:self.glassCard];
    
    [NSLayoutConstraint activateConstraints:@[
        [self.glassCard.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
        [self.glassCard.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
        [self.glassCard.widthAnchor constraintEqualToAnchor:self.view.widthAnchor multiplier:0.85],
        [self.glassCard.widthAnchor constraintLessThanOrEqualToConstant:340]
    ]];

    UIStackView *mainStack = [[UIStackView alloc] init];
    mainStack.axis = UILayoutConstraintAxisVertical;
    mainStack.spacing = 24;
    mainStack.translatesAutoresizingMaskIntoConstraints = NO;
    [self.glassCard addSubview:mainStack];

    [NSLayoutConstraint activateConstraints:@[
        [mainStack.topAnchor constraintEqualToAnchor:self.glassCard.topAnchor constant:28],
        [mainStack.bottomAnchor constraintEqualToAnchor:self.glassCard.bottomAnchor constant:-28],
        [mainStack.leadingAnchor constraintEqualToAnchor:self.glassCard.leadingAnchor constant:24],
        [mainStack.trailingAnchor constraintEqualToAnchor:self.glassCard.trailingAnchor constant:-24]
    ]];

    UIStackView *headerStack = [[UIStackView alloc] init];
    headerStack.axis = UILayoutConstraintAxisHorizontal;
    headerStack.spacing = 16;
    headerStack.alignment = UIStackViewAlignmentCenter;
    [mainStack addArrangedSubview:headerStack];

    self.logoView = [[UIImageView alloc] init];
    self.logoView.contentMode = UIViewContentModeScaleAspectFill;
    self.logoView.layer.cornerRadius = 14; 
    self.logoView.clipsToBounds = YES;
    self.logoView.layer.borderWidth = 1.0;
    self.logoView.layer.borderColor = [UIColor colorWithWhite:0.0 alpha:0.1].CGColor;
    self.logoView.translatesAutoresizingMaskIntoConstraints = NO;
    [headerStack addArrangedSubview:self.logoView];

    [NSLayoutConstraint activateConstraints:@[
        [self.logoView.widthAnchor constraintEqualToConstant:65],
        [self.logoView.heightAnchor constraintEqualToConstant:65]
    ]];

    [self loadAndCacheImage:@"https://ashtemobile.site/a.png" forImageView:self.logoView placeholder:@"app.fill"];

    UIStackView *titleStack = [[UIStackView alloc] init];
    titleStack.axis = UILayoutConstraintAxisVertical;
    titleStack.spacing = 4;
    [headerStack addArrangedSubview:titleStack];

    UILabel *titleLabel = [[UILabel alloc] init];
    titleLabel.text = @"AshteMobile"; 
    titleLabel.font = [UIFont systemFontOfSize:22 weight:UIFontWeightHeavy];
    titleLabel.textColor = [UIColor blackColor]; 
    [titleStack addArrangedSubview:titleLabel];

    UILabel *subLabel = [[UILabel alloc] init];
    subLabel.text = @"Premium iOS Mod";
    subLabel.font = [UIFont systemFontOfSize:14 weight:UIFontWeightSemibold];
    subLabel.textColor = [UIColor systemBlueColor]; 
    [titleStack addArrangedSubview:subLabel];

    UIView *divider = [[UIView alloc] init];
    divider.backgroundColor = [UIColor colorWithWhite:0.0 alpha:0.08];
    [divider.heightAnchor constraintEqualToConstant:1].active = YES;
    [mainStack addArrangedSubview:divider];

    UIStackView *dockStack = [[UIStackView alloc] init];
    dockStack.axis = UILayoutConstraintAxisHorizontal;
    dockStack.spacing = 16;
    dockStack.distribution = UIStackViewDistributionFillEqually;
    [mainStack addArrangedSubview:dockStack];

    [NSLayoutConstraint activateConstraints:@[
        [dockStack.widthAnchor constraintEqualToAnchor:mainStack.widthAnchor]
    ]];

    UIButton *tgBtn = [self createModernBlockButton:@"https://img.icons8.com/color/100/telegram-app.png" placeholder:@"paperplane.fill" action:@selector(openTelegram)];
    UIButton *webBtn = [self createModernBlockButton:@"https://img.icons8.com/color/100/safari--v1.png" placeholder:@"safari.fill" action:@selector(openWebsite)];
    UIButton *ttBtn = [self createModernBlockButton:@"https://img.icons8.com/fluency/100/tiktok.png" placeholder:@"play.tv.fill" action:@selector(openTikTok)];

    [dockStack addArrangedSubview:tgBtn];
    [dockStack addArrangedSubview:webBtn];
    [dockStack addArrangedSubview:ttBtn];

    UIButton *startBtn = [UIButton buttonWithType:UIButtonTypeSystem];
    startBtn.backgroundColor = [UIColor systemBlueColor]; 
    startBtn.layer.cornerRadius = 14; 
    [startBtn setTitle:@"OPEN" forState:UIControlStateNormal];
    [startBtn setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    startBtn.titleLabel.font = [UIFont systemFontOfSize:17 weight:UIFontWeightHeavy];
    
    startBtn.layer.shadowColor = [UIColor systemBlueColor].CGColor;
    startBtn.layer.shadowOpacity = 0.3;
    startBtn.layer.shadowOffset = CGSizeMake(0, 4);
    startBtn.layer.shadowRadius = 8;
    
    [startBtn addTarget:self action:@selector(closeTapped) forControlEvents:UIControlEventTouchUpInside];
    [mainStack addArrangedSubview:startBtn];

    [NSLayoutConstraint activateConstraints:@[
        [startBtn.widthAnchor constraintEqualToAnchor:mainStack.widthAnchor],
        [startBtn.heightAnchor constraintEqualToConstant:54] 
    ]];
}

- (void)viewDidAppear:(BOOL)animated {
    [super viewDidAppear:animated];
    [UIView animateWithDuration:0.5 delay:0.0 usingSpringWithDamping:0.75 initialSpringVelocity:0.5 options:UIViewAnimationOptionCurveEaseOut animations:^{
        self.glassCard.alpha = 1.0;
        self.glassCard.transform = CGAffineTransformIdentity;
    } completion:nil];
}

- (void)loadAndCacheImage:(NSString *)urlStr forImageView:(UIImageView *)imgView placeholder:(NSString *)sysName {
    if (sysName) {
        imgView.image = [UIImage systemImageNamed:sysName];
        imgView.tintColor = [UIColor colorWithWhite:0.0 alpha:0.3];
    }
    
    NSString *docDir = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
    NSString *safeName = [[urlStr componentsSeparatedByString:@"/"] lastObject];
    NSString *cachePath = [docDir stringByAppendingPathComponent:safeName];
    
    NSData *cachedData = [NSData dataWithContentsOfFile:cachePath];
    
    if (cachedData) {
        imgView.image = [UIImage imageWithData:cachedData];
    } else {
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_HIGH, 0), ^{
            NSData *data = [NSData dataWithContentsOfURL:[NSURL URLWithString:urlStr]];
            if (data) {
                [data writeToFile:cachePath atomically:YES];
                dispatch_async(dispatch_get_main_queue(), ^{
                    imgView.image = [UIImage imageWithData:data];
                });
            }
        });
    }
}

- (UIButton *)createModernBlockButton:(NSString *)url placeholder:(NSString *)ph action:(SEL)action {
    UIButton *btn = [UIButton buttonWithType:UIButtonTypeCustom];
    btn.backgroundColor = [UIColor colorWithWhite:0.0 alpha:0.04];
    btn.layer.cornerRadius = 14; 
    btn.layer.borderWidth = 1.0;
    btn.layer.borderColor = [UIColor colorWithWhite:0.0 alpha:0.05].CGColor;
    [btn addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];

    UIImageView *icon = [[UIImageView alloc] init];
    icon.contentMode = UIViewContentModeScaleAspectFit;
    icon.translatesAutoresizingMaskIntoConstraints = NO;
    [btn addSubview:icon];

    [NSLayoutConstraint activateConstraints:@[
        [btn.heightAnchor constraintEqualToConstant:60], 
        [icon.centerXAnchor constraintEqualToAnchor:btn.centerXAnchor],
        [icon.centerYAnchor constraintEqualToAnchor:btn.centerYAnchor],
        [icon.widthAnchor constraintEqualToConstant:32],
        [icon.heightAnchor constraintEqualToConstant:32]
    ]];

    [self loadAndCacheImage:url forImageView:icon placeholder:ph];

    return btn;
}

- (void)playHaptic {
    UIImpactFeedbackGenerator *gen = [[UIImpactFeedbackGenerator alloc] initWithStyle:UIImpactFeedbackStyleMedium];
    [gen impactOccurred];
}

- (void)openTelegram { 
    [self playHaptic]; 
    [[UIApplication sharedApplication] openURL:[NSURL URLWithString:@"https://t.me/ashtemobile"] options:@{} completionHandler:nil]; 
}

- (void)openWebsite { 
    [self playHaptic]; 
    [[UIApplication sharedApplication] openURL:[NSURL URLWithString:@"https://ashtemobile.site"] options:@{} completionHandler:nil]; 
}

- (void)openTikTok { 
    [self playHaptic]; 
    [[UIApplication sharedApplication] openURL:[NSURL URLWithString:@"https://www.tiktok.com/@ashtemobile"] options:@{} completionHandler:nil]; 
}

- (void)closeTapped {
    [self playHaptic];
    [UIView animateWithDuration:0.3 animations:^{
        self.view.alpha = 0.0; 
        self.glassCard.transform = CGAffineTransformMakeScale(0.9, 0.9);
    } completion:^(BOOL finished) {
        [self dismissViewControllerAnimated:NO completion:nil];
    }];
}

@end

// --- بەشی ئینجێکتکردن ---
__attribute__((constructor)) static void showCustomWelcomeScreen() {
    [[NSNotificationCenter defaultCenter] addObserverForName:UIApplicationDidBecomeActiveNotification object:nil queue:[NSOperationQueue mainQueue] usingBlock:^(NSNotification *note) {
        static dispatch_once_t onceToken;
        dispatch_once(&onceToken, ^{
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
                
                UIWindow *keyWindow = nil;
                for (UIWindow *window in [UIApplication sharedApplication].windows) {
                    if (window.isKeyWindow) { keyWindow = window; break; }
                }
                if (keyWindow && keyWindow.rootViewController) {
                    UIViewController *topController = keyWindow.rootViewController;
                    while (topController.presentedViewController) { topController = topController.presentedViewController; }
                    AshteWelcomeViewController *welcomeVC = [[AshteWelcomeViewController alloc] init];
                    
                    welcomeVC.modalPresentationStyle = UIModalPresentationOverFullScreen;
                    
                    [topController presentViewController:welcomeVC animated:NO completion:nil];
                }
            });
        });
    }];
}
