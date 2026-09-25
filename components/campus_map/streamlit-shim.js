/* Minimal, self-hosted implementation of the bits of `streamlit-component-lib`
 * that this map component needs.
 *
 * The npm package no longer ships a browser bundle (the old unpkg URL 404s), so
 * the four message types of the component wire protocol are implemented here
 * directly. Protocol reference: streamlit/components/types/base_custom_component.py
 *
 *   component -> parent  { isStreamlitMessage, type, ... }
 *   parent     -> component { type: "streamlit:render", args, dfs, disabled, theme }
 */
(function () {
  "use strict";

  var API_VERSION = 1;

  function post(message) {
    if (window.parent === window) {
      return;
    }
    message.isStreamlitMessage = true;
    window.parent.postMessage(message, "*");
  }

  window.Streamlit = {
    /** Tell Streamlit the component booted, so it starts sending render args. */
    setComponentReady: function () {
      post({ type: "streamlit:componentReady", apiVersion: API_VERSION });
    },

    /** Size the iframe. Streamlit keeps it hidden until setComponentReady lands. */
    setFrameHeight: function (height) {
      post({ type: "streamlit:setFrameHeight", height: height });
    },

    /** Send a value back to Python; dataType "json" (default), "dataframe" or "bytes". */
    setComponentValue: function (value, dataType) {
      post({
        type: "streamlit:setComponentValue",
        value: value,
        dataType: dataType || "json"
      });
    },

    Rerun: function () {
      post({ type: "streamlit:rerun_request" });
    }
  };
})();
