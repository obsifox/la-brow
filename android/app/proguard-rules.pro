-keep class org.mozilla.geckoview.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
