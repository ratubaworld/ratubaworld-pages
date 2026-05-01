(function () {
  function stampAll(text) {
    document.querySelectorAll(".build-stamp").forEach(function (el) {
      el.textContent = text;
    });
  }

  function fmtUtc(iso) {
    try {
      return new Date(iso).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch (e) {
      return iso;
    }
  }

  fetch("version.json", { cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("version.json");
      return r.json();
    })
    .then(function (v) {
      var ver = (v.version || "0.0.0").replace(/^v/i, "");
      var repo = v.repo || "ratubaworld/ratubaworld-pages";
      var ref = v.ref || "main";

      stampAll("v" + ver + " \u2014 fetching commit\u2026");

      var url =
        "https://api.github.com/repos/" + repo + "/commits/" + encodeURIComponent(ref);
      return fetch(url, {
        headers: { Accept: "application/vnd.github+json" },
      })
        .then(function (cr) {
          if (!cr.ok) throw new Error("commits api");
          return cr.json().then(function (c) {
            var iso =
              (c.commit && c.commit.committer && c.commit.committer.date) ||
              (c.commit && c.commit.author && c.commit.author.date) ||
              "";
            var sha = (c.sha || "").slice(0, 7);
            var when = iso ? fmtUtc(iso) : "unknown time";
            var line = "v" + ver + " — " + when + (sha ? " (" + sha + ")" : "");
            stampAll(line);
          });
        })
        .catch(function () {
          stampAll(
            "v" + ver + " — (live commit time unavailable; check api rate limits)"
          );
        });
    })
    .catch(function () {
      stampAll("(version unavailable)");
    });
})();
