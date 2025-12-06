(function () {
  function setDisabled(select, disabled) {
    if (!select) {
      return;
    }
    if (disabled) {
      select.setAttribute("disabled", "disabled");
    } else {
      select.removeAttribute("disabled");
    }
  }

  function fetchOptions(url, paramName, value) {
    if (!value) {
      return Promise.resolve([]);
    }
    const separator = url.includes("?") ? "&" : "?";
    return fetch(`${url}${separator}${paramName}=${encodeURIComponent(value)}`, {
      credentials: "include",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load options");
        }
        return response.json();
      })
      .then((data) => data.results || [])
      .catch(() => []);
  }

  function populateSelect(select, options, currentValue) {
    if (!select) {
      return;
    }
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "---------";
    select.innerHTML = "";
    select.appendChild(placeholder);

    options.forEach((option) => {
      const opt = document.createElement("option");
      opt.value = option.id;
      opt.textContent = option.name;
      if (currentValue && currentValue === String(option.id)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }

  function resetSelect(select) {
    if (!select) {
      return;
    }
    select.value = "";
    select.dataset.currentValue = "";
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "---------";
    select.appendChild(placeholder);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const siteSelect = document.getElementById("id_site");
    const areaSelect = document.getElementById("id_area");
    const rackSelect = document.getElementById("id_rack");

    if (!siteSelect || !areaSelect || !rackSelect) {
      return;
    }

    const areasUrl = siteSelect.dataset.areasUrl;
    const racksUrl = areaSelect.dataset.racksUrl;

    function loadAreasForSite(siteId, retainCurrent) {
      resetSelect(areaSelect);
      resetSelect(rackSelect);
      if (!siteId || !areasUrl) {
        setDisabled(areaSelect, true);
        setDisabled(rackSelect, true);
        return;
      }
      setDisabled(areaSelect, false);
      const targetValue = retainCurrent
        ? areaSelect.dataset.currentValue
        : "";
      fetchOptions(areasUrl, "site", siteId).then((areas) => {
        populateSelect(areaSelect, areas, targetValue);
        if (targetValue) {
          loadRacksForArea(targetValue, true);
        } else {
          setDisabled(rackSelect, true);
        }
      });
    }

    function loadRacksForArea(areaId, retainCurrent) {
      resetSelect(rackSelect);
      if (!areaId || !racksUrl) {
        setDisabled(rackSelect, true);
        return;
      }
      setDisabled(rackSelect, false);
      const targetValue = retainCurrent
        ? rackSelect.dataset.currentValue
        : "";
      fetchOptions(racksUrl, "area", areaId).then((racks) => {
        populateSelect(rackSelect, racks, targetValue);
      });
    }

    siteSelect.addEventListener("change", function (event) {
      const siteId = event.target.value;
      areaSelect.dataset.currentValue = "";
      rackSelect.dataset.currentValue = "";
      if (!siteId) {
        resetSelect(areaSelect);
        resetSelect(rackSelect);
        setDisabled(areaSelect, true);
        setDisabled(rackSelect, true);
        return;
      }
      loadAreasForSite(siteId, false);
    });

    areaSelect.addEventListener("change", function (event) {
      const areaId = event.target.value;
      rackSelect.dataset.currentValue = "";
      if (!areaId) {
        resetSelect(rackSelect);
        setDisabled(rackSelect, true);
        return;
      }
      loadRacksForArea(areaId, false);
    });

    // Populate on initial load if editing existing object
    if (siteSelect.value) {
      loadAreasForSite(siteSelect.value, true);
    } else {
      setDisabled(areaSelect, true);
      setDisabled(rackSelect, true);
    }
    if (areaSelect.dataset.currentValue) {
      loadRacksForArea(areaSelect.dataset.currentValue, true);
    } else if (!siteSelect.value) {
      setDisabled(rackSelect, true);
    }
  });
})();
