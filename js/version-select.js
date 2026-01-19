window.addEventListener("DOMContentLoaded", function () {
  function expandPath(path) {
    // Get the base directory components.
    var expanded = window.location.pathname.split("/");
    expanded.pop();
    var isSubdir = false;

    path.split("/").forEach(function (bit, i) {
      if (bit === "" && i === 0) {
        isSubdir = false;
        expanded = [""];
      } else if (bit === "." || bit === "") {
        isSubdir = true;
      } else if (bit === "..") {
        if (expanded.length === 1) {
          // We must be trying to .. past the root!
          throw new Error("invalid path");
        } else {
          isSubdir = true;
          expanded.pop();
        }
      } else {
        isSubdir = false;
        expanded.push(bit);
      }
    });

    if (isSubdir)
      expanded.push("");
    return expanded.join("/");
  }

  // `base_url` comes from the base.html template for this theme.
  var ABS_BASE_URL = expandPath(base_url);
  try {
    var CURRENT_VERSION = ABS_BASE_URL.match(/\/([^\/]+)\/$/)[1];
  } catch (error) {
    console.warn("Failed to parse current version:", error, ". Versioning not enabled?");
    return;
  }
  var CURRENT_PATH = (new URL(window.location.href)).pathname.slice(ABS_BASE_URL.length);

  function makeSelect(options) {
    var select = document.createElement("select");

    options.forEach(function (i) {
      var option = new Option(i.text, i.value, undefined,
        i.selected);
      select.add(option);
    });

    return select;
  }

  fetch(ABS_BASE_URL + "../versions.json").then((response) => {
    return response.json();
  }).then((versions) => {
    var realVersion = versions.find(function (i) {
      return i.version === CURRENT_VERSION ||
        i.aliases.includes(CURRENT_VERSION);
    }).version;

    var select = makeSelect(versions.filter(function (i) {
      return i.version === realVersion || !i.properties || !i.properties.hidden;
    }).map(function (i) {
      return {
        text: i.title, value: i.version,
        selected: i.version === realVersion
      };
    }));
    select.id = "version-selector";
    select.addEventListener("change", function (event) {
      window.location.href = ABS_BASE_URL + "../" + this.value + "/" + CURRENT_PATH;
    });

    var container = document.getElementById("mike-versions");
    container.appendChild(select);
  }).catch((error) => {
    console.error("Failed to fetch versions.json:", error);
  });
});
