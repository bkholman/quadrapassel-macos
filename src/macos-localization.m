/* SPDX-License-Identifier: GPL-3.0-or-later */
#import <Foundation/Foundation.h>
#include "macos-support.h"

gchar **
quadrapassel_macos_preferred_languages (void)
{
    @autoreleasepool {
        NSArray<NSString *> *languages = [NSLocale preferredLanguages];
        gchar **result = g_new0 (gchar *, languages.count + 1);
        for (NSUInteger i = 0; i < languages.count; i++)
            result[i] = g_strdup ([languages[i] UTF8String]);
        return result;
    }
}

void
quadrapassel_macos_set_process_language (const gchar *language)
{
    @autoreleasepool {
        NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
        NSMutableDictionary *arguments = [[defaults volatileDomainForName:NSArgumentDomain] mutableCopy];
        if (arguments == nil)
            arguments = [[NSMutableDictionary alloc] init];
        arguments[@"AppleLanguages"] = @[[NSString stringWithUTF8String:language]];
        // A volatile domain affects only this process. Never write the user's
        // global or per-application macOS language preferences.
        [defaults setVolatileDomain:arguments forName:NSArgumentDomain];
        [arguments release];
    }
}
