package com.bondhop.angrybirds;

import android.app.Activity;
import android.webkit.JavascriptInterface;

/** Exposed to the game's JavaScript as window.Android. */
public class GameBridge implements Runnable {
    private final Activity activity;

    public GameBridge(Activity activity) {
        this.activity = activity;
    }

    @JavascriptInterface
    public void quit() {
        activity.runOnUiThread(this);
    }

    @Override
    public void run() {
        activity.finish();
    }
}
