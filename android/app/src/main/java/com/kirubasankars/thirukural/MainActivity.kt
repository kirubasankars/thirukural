package com.kirubasankars.thirukural

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.webkit.WebViewAssetLoader

/**
 * Shows the published Thirukkural deck from the app assets.
 *
 * Back closes search, then moves to the previous verse, then leaves the app.
 */
class MainActivity : ComponentActivity() {
    private lateinit var deck: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        deck = WebView(this)
        setContentView(deck)

        deck.setBackgroundColor(Color.parseColor("#222222"))
        deck.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            useWideViewPort = true
            loadWithOverviewMode = true
            builtInZoomControls = false
            displayZoomControls = false
            textZoom = 100
        }

        val assets = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
        deck.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView,
                request: WebResourceRequest,
            ): WebResourceResponse? = assets.shouldInterceptRequest(request.url)
        }

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    deck.evaluateJavascript(BACK_HANDLER) { result ->
                        if (result == "\"exit\"") finish()
                    }
                }
            },
        )

        if (savedInstanceState == null) {
            deck.loadUrl(DECK_URL)
        } else {
            deck.restoreState(savedInstanceState)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        deck.saveState(outState)
        super.onSaveInstanceState(outState)
    }
}

private const val DECK_URL = "https://appassets.androidplatform.net/assets/index.html"

private const val BACK_HANDLER = """
(function () {
  var panel = document.getElementById("kural-search");
  if (panel && !panel.hidden) {
    var closeButton = document.getElementById("kural-search-close");
    if (closeButton) closeButton.click();
    return "search";
  }
  if (window.Reveal && typeof Reveal.isFirstSlide === "function" && !Reveal.isFirstSlide()) {
    Reveal.prev();
    return "prev";
  }
  return "exit";
})()
"""
