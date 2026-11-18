# The JavaScript bridge is invoked by name from WebView JavaScript.
-keepclassmembers class com.pemaratech.maestrostudio.BlobDownloadBridge {
    @android.webkit.JavascriptInterface <methods>;
}
