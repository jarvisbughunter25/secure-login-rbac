(() => {
  const USERNAME_REGEX = /^[A-Za-z0-9_]{3,30}$/;
  const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const THEME_STORAGE_KEY = "sap-theme";
  const PASSWORD_RULES = [
    { regex: /.{10,}/, label: "at least 10 characters" },
    { regex: /[A-Z]/, label: "an uppercase letter" },
    { regex: /[a-z]/, label: "a lowercase letter" },
    { regex: /\d/, label: "a number" },
    { regex: /[^A-Za-z0-9]/, label: "a special character" },
  ];

  function clearClientErrors(form) {
    form.querySelectorAll(".client-error").forEach((el) => el.remove());
  }

  function addError(field, message) {
    const note = document.createElement("p");
    note.className = "client-error";
    note.textContent = message;
    field.insertAdjacentElement("afterend", note);
  }

  function passwordErrors(value) {
    return PASSWORD_RULES.filter((rule) => !rule.regex.test(value)).map((rule) => rule.label);
  }

  function validateRegister(form) {
    let ok = true;

    const username = form.querySelector("#username");
    if (username && !USERNAME_REGEX.test(username.value.trim())) {
      addError(username, "Username must be 3-30 chars and use only letters, numbers, underscore.");
      ok = false;
    }

    const email = form.querySelector("#email");
    if (email && !EMAIL_REGEX.test(email.value.trim())) {
      addError(email, "Enter a valid email address.");
      ok = false;
    }

    const password = form.querySelector("#password");
    if (password) {
      const failures = passwordErrors(password.value);
      if (failures.length) {
        addError(password, `Password must include ${failures.join(", ")}.`);
        ok = false;
      }
    }

    const role = form.querySelector("#role");
    if (role && !role.value) {
      addError(role, "Please select a role.");
      ok = false;
    }

    const captchaAnswer = form.querySelector("#captcha_answer");
    if (captchaAnswer && !captchaAnswer.value.trim()) {
      addError(captchaAnswer, "Captcha answer is required.");
      ok = false;
    }

    return ok;
  }

  function validateLogin(form) {
    let ok = true;

    const email = form.querySelector("#email");
    if (email && !EMAIL_REGEX.test(email.value.trim())) {
      addError(email, "Enter a valid email address.");
      ok = false;
    }

    const password = form.querySelector("#password");
    if (password && !password.value.trim()) {
      addError(password, "Password is required.");
      ok = false;
    }

    const captchaAnswer = form.querySelector("#captcha_answer");
    if (captchaAnswer && !captchaAnswer.value.trim()) {
      addError(captchaAnswer, "Captcha answer is required.");
      ok = false;
    }

    return ok;
  }

  function bindValidation(form) {
    const mode = form.dataset.validate;

    form.addEventListener("submit", (event) => {
      clearClientErrors(form);
      let valid = true;

      if (mode === "register") {
        valid = validateRegister(form);
      } else if (mode === "login") {
        valid = validateLogin(form);
      }

      if (!valid) {
        event.preventDefault();
      }
    });
  }

  function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function setTheme(theme) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", nextTheme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch (_error) {
      // Ignore storage failures and keep runtime theme.
    }
  }

  function bindThemeToggle() {
    const toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) {
      return;
    }

    const label = toggle.querySelector("[data-theme-label]");
    const icon = toggle.querySelector("[data-theme-icon]");
    const syncState = () => {
      const darkMode = getTheme() === "dark";
      toggle.classList.toggle("is-dark", darkMode);
      toggle.setAttribute("aria-pressed", darkMode ? "true" : "false");
      toggle.setAttribute("aria-label", darkMode ? "Switch to light mode" : "Switch to dark mode");
      toggle.setAttribute("title", darkMode ? "Switch to light mode" : "Switch to dark mode");
      if (label) {
        label.textContent = darkMode ? "Dark" : "Light";
      }
      if (icon) {
        icon.setAttribute("data-icon", darkMode ? "sun" : "moon");
      }
    };

    toggle.addEventListener("click", () => {
      const nextTheme = getTheme() === "dark" ? "light" : "dark";
      setTheme(nextTheme);
      syncState();
    });

    syncState();
  }

  function bindPasswordToggles() {
    document.querySelectorAll("input[data-password-toggle='true']").forEach((field) => {
      if (field.dataset.toggleBound === "true") {
        return;
      }
      field.dataset.toggleBound = "true";

      const wrapper = document.createElement("div");
      wrapper.className = "password-wrap";
      field.parentNode.insertBefore(wrapper, field);
      wrapper.appendChild(field);

      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "password-toggle";
      toggle.textContent = "show";
      toggle.setAttribute("aria-label", "Show password");
      toggle.setAttribute("aria-pressed", "false");
      wrapper.appendChild(toggle);

      toggle.addEventListener("click", () => {
        const makeVisible = field.type === "password";
        field.type = makeVisible ? "text" : "password";
        toggle.textContent = makeVisible ? "hide" : "show";
        toggle.setAttribute("aria-label", makeVisible ? "Hide password" : "Show password");
        toggle.setAttribute("aria-pressed", makeVisible ? "true" : "false");
      });
    });
  }

  function passwordStrengthState(value) {
    const score = PASSWORD_RULES.reduce((total, rule) => total + Number(rule.regex.test(value)), 0);

    if (score <= 1) {
      return { level: "low", label: "Low", progress: 25, score };
    }
    if (score <= 3) {
      return { level: "medium", label: "Medium", progress: 55, score };
    }
    if (score === 4) {
      return { level: "hard", label: "Hard", progress: 78, score };
    }
    return { level: "excellent", label: "Excellent", progress: 100, score };
  }

  function bindPasswordStrengthMeters() {
    document.querySelectorAll("input[data-password-strength='true']").forEach((field) => {
      if (field.dataset.strengthBound === "true") {
        return;
      }
      field.dataset.strengthBound = "true";

      const meter = document.createElement("div");
      meter.className = "password-strength";
      meter.setAttribute("aria-live", "polite");
      meter.innerHTML = `
        <div class="password-strength-head">
          <span class="password-strength-label">Password strength</span>
          <span class="password-strength-chip" data-strength-chip>Low</span>
        </div>
        <div class="password-strength-track">
          <span class="password-strength-fill" data-strength-fill></span>
        </div>
        <p class="password-strength-meta" data-strength-meta>0 / 5 checks passed</p>
      `;

      const anchor = field.closest(".password-wrap") || field;
      const next = anchor.nextElementSibling;
      if (next && next.classList.contains("hint")) {
        next.insertAdjacentElement("afterend", meter);
      } else {
        anchor.insertAdjacentElement("afterend", meter);
      }

      const chip = meter.querySelector("[data-strength-chip]");
      const fill = meter.querySelector("[data-strength-fill]");
      const meta = meter.querySelector("[data-strength-meta]");

      const render = () => {
        const value = field.value || "";
        if (!value) {
          meter.classList.remove("is-visible");
          meter.removeAttribute("data-level");
          if (fill) {
            fill.style.width = "0%";
          }
          if (chip) {
            chip.textContent = "Low";
          }
          if (meta) {
            meta.textContent = "0 / 5 checks passed";
          }
          return;
        }

        const state = passwordStrengthState(value);
        meter.classList.add("is-visible");
        meter.dataset.level = state.level;
        if (fill) {
          fill.style.width = `${state.progress}%`;
        }
        if (chip) {
          chip.textContent = state.label;
        }
        if (meta) {
          meta.textContent = `${state.score} / 5 checks passed`;
        }
      };

      field.addEventListener("input", render);
      field.addEventListener("blur", render);
      render();
    });
  }

  function bindFilePickers() {
    document.querySelectorAll("[data-file-picker]").forEach((picker) => {
      const input = picker.querySelector("[data-file-input]");
      const trigger = picker.querySelector("[data-file-trigger]");
      const filename = picker.querySelector("[data-file-name]");
      const clearButton = picker.querySelector("[data-file-clear]");

      if (!input || !trigger || !filename || !clearButton) {
        return;
      }

      const syncFileName = () => {
        const hasFile = Boolean(input.files && input.files.length > 0);
        filename.textContent = hasFile ? input.files[0].name : "No file selected";
        clearButton.hidden = !hasFile;
      };

      trigger.addEventListener("click", () => {
        input.click();
      });

      clearButton.addEventListener("click", () => {
        input.value = "";
        syncFileName();
        input.focus();
      });

      input.addEventListener("change", syncFileName);
      syncFileName();
    });
  }

  function bindInputClearButtons() {
    document.querySelectorAll("[data-clear-field]").forEach((button) => {
      const selector = button.dataset.clearTarget;
      const target = selector
        ? document.querySelector(selector)
        : button.closest(".input-inline-wrap")?.querySelector("input, textarea");

      if (!target) {
        return;
      }

      button.addEventListener("click", () => {
        target.value = "";
        target.focus();
      });
    });
  }

  function bindCaptchaRefresh() {
    document.querySelectorAll("[data-captcha-refresh]").forEach((button) => {
      const url = button.dataset.captchaUrl;
      if (!url) {
        return;
      }

      button.addEventListener("click", async () => {
        const form = button.closest("form");
        const question = form?.querySelector("[data-captcha-question]");
        if (!question) {
          return;
        }

        const originalLabel = button.textContent;
        button.disabled = true;
        button.textContent = "loading";

        try {
          const response = await fetch(url, {
            method: "GET",
            headers: {
              Accept: "application/json",
              "X-Requested-With": "XMLHttpRequest",
            },
            credentials: "same-origin",
          });

          if (!response.ok) {
            return;
          }

          const payload = await response.json();
          if (payload.question) {
            question.textContent = payload.question;
            const answerInput = form.querySelector("#captcha_answer");
            if (answerInput) {
              answerInput.value = "";
              answerInput.focus();
            }
          }
        } catch (_error) {
          // Keep current challenge if refresh fails.
        } finally {
          button.disabled = false;
          button.textContent = originalLabel;
        }
      });
    });
  }

  function bindProfileMenu() {
    const menu = document.querySelector("[data-profile-menu]");
    if (!menu) {
      return;
    }

    const button = menu.querySelector(".profile-toggle");
    if (!button) {
      return;
    }

    const submenuContainers = Array.from(menu.querySelectorAll("[data-profile-submenu]"));
    const closeSubmenus = () => {
      submenuContainers.forEach((container) => {
        container.classList.remove("open");
        const toggle = container.querySelector("[data-submenu-toggle]");
        if (toggle) {
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    };
    const closeMenu = () => {
      menu.classList.remove("open");
      button.setAttribute("aria-expanded", "false");
      closeSubmenus();
    };

    submenuContainers.forEach((container) => {
      const toggle = container.querySelector("[data-submenu-toggle]");
      if (!toggle) {
        return;
      }

      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const willOpen = !container.classList.contains("open");
        closeSubmenus();
        if (willOpen) {
          container.classList.add("open");
          toggle.setAttribute("aria-expanded", "true");
        }
      });
    });

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = menu.classList.toggle("open");
      button.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (!isOpen) {
        closeSubmenus();
      }
    });

    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) {
        closeMenu();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu();
      }
    });
  }

  function createConfirmModalController() {
    const backdrop = document.querySelector("[data-confirm-modal]");
    if (!backdrop) {
      return null;
    }

    const title = backdrop.querySelector("[data-confirm-title]");
    const message = backdrop.querySelector("[data-confirm-message]");
    const cancelButton = backdrop.querySelector("[data-confirm-cancel]");
    const confirmButton = backdrop.querySelector("[data-confirm-accept]");
    const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (!title || !message || !cancelButton || !confirmButton) {
      return null;
    }

    let resolver = null;
    let lastFocused = null;
    let closing = false;

    const finish = (accepted) => {
      if (!resolver || closing) {
        return;
      }
      closing = true;
      backdrop.classList.remove("is-open");
      document.body.classList.remove("modal-open");
      document.removeEventListener("keydown", onKeydown);

      const finalize = () => {
        backdrop.hidden = true;
        const resolveFn = resolver;
        resolver = null;
        closing = false;
        if (lastFocused && typeof lastFocused.focus === "function") {
          lastFocused.focus();
        }
        resolveFn(accepted);
      };

      if (reducedMotion) {
        finalize();
        return;
      }

      window.setTimeout(finalize, 240);
    };

    const onKeydown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        finish(false);
        return;
      }

      if (event.key === "Tab") {
        const focusable = [cancelButton, confirmButton].filter((node) => !node.disabled);
        if (!focusable.length) {
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };

    cancelButton.addEventListener("click", () => finish(false));
    confirmButton.addEventListener("click", () => finish(true));

    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) {
        finish(false);
      }
    });

    return {
      open(options = {}) {
        if (resolver) {
          return Promise.resolve(false);
        }

        title.textContent = options.title || "Confirm Action";
        message.textContent = options.message || "Do you want to continue?";
        cancelButton.textContent = options.cancelLabel || "Cancel";
        confirmButton.textContent = options.confirmLabel || "Confirm";
        confirmButton.classList.toggle("is-danger", options.variant === "danger");

        lastFocused = document.activeElement;
        backdrop.hidden = false;
        document.body.classList.add("modal-open");
        window.requestAnimationFrame(() => {
          backdrop.classList.add("is-open");
          cancelButton.focus();
        });
        document.addEventListener("keydown", onKeydown);

        return new Promise((resolve) => {
          resolver = resolve;
        });
      },
    };
  }

  function bindConfirmationForms() {
    const confirmModal = createConfirmModalController();

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        if (form.dataset.confirmBypass === "true") {
          form.dataset.confirmBypass = "false";
          return;
        }

        event.preventDefault();

        const options = {
          title: form.dataset.confirmTitle || "Confirm Action",
          message: form.dataset.confirm || "Are you sure?",
          confirmLabel: form.dataset.confirmOk || "Confirm",
          cancelLabel: form.dataset.confirmCancel || "Cancel",
          variant: form.dataset.confirmVariant || "default",
        };

        const proceed = (accepted) => {
          if (!accepted) {
            return;
          }
          form.dataset.confirmBypass = "true";
          if (typeof form.requestSubmit === "function") {
            if (event.submitter) {
              form.requestSubmit(event.submitter);
            } else {
              form.requestSubmit();
            }
          } else {
            form.submit();
          }
        };

        if (!confirmModal) {
          proceed(window.confirm(options.message));
          return;
        }

        confirmModal.open(options).then(proceed);
      });
    });
  }

  function bindAdminSearch() {
    const searchInput = document.querySelector("#adminUserSearch");
    if (!searchInput) {
      return;
    }

    const rows = Array.from(document.querySelectorAll("[data-user-row]"));
    const filterRows = () => {
      const query = searchInput.value.trim().toLowerCase();
      rows.forEach((row) => {
        const text = row.dataset.search || "";
        row.style.display = !query || text.includes(query) ? "" : "none";
      });
    };

    searchInput.addEventListener("input", filterRows);
  }

  function cleanupFlashStack(stack) {
    if (stack && stack.children.length === 0) {
      stack.remove();
    }
  }

  function dismissFlash(flash, stack, reducedMotion) {
    if (!flash || flash.dataset.dismissed === "true") {
      return;
    }
    flash.dataset.dismissed = "true";

    if (reducedMotion) {
      flash.remove();
      cleanupFlashStack(stack);
      return;
    }

    flash.style.maxHeight = `${flash.scrollHeight}px`;
    window.requestAnimationFrame(() => {
      flash.classList.add("is-dismissing");
      flash.style.maxHeight = "0px";
    });

    let finalized = false;
    const finalize = () => {
      if (finalized) {
        return;
      }
      finalized = true;
      flash.remove();
      cleanupFlashStack(stack);
    };

    flash.addEventListener("transitionend", finalize, { once: true });
    window.setTimeout(finalize, 520);
  }

  function bindFlashAutoDismiss() {
    const stack = document.querySelector(".flash-stack");
    if (!stack) {
      return;
    }

    const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    stack.querySelectorAll(".flash").forEach((flash, index) => {
      window.setTimeout(() => dismissFlash(flash, stack, reducedMotion), 3000 + index * 120);
    });
  }

  window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-validate]").forEach((form) => bindValidation(form));
    bindThemeToggle();
    bindProfileMenu();
    bindPasswordToggles();
    bindPasswordStrengthMeters();
    bindFilePickers();
    bindInputClearButtons();
    bindCaptchaRefresh();
    bindConfirmationForms();
    bindAdminSearch();
    bindFlashAutoDismiss();
  });
})();
