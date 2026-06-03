const fileInput = document.querySelector("#reference-input");
const preview = document.querySelector("#preview");
const form = document.querySelector("#post-form");
const loading = document.querySelector("#loading");
const promptInput = document.querySelector("#main-prompt");
const tokenCount = document.querySelector("#token-count");

if (fileInput && preview) {
  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (!file) {
      preview.hidden = true;
      preview.removeAttribute("src");
      return;
    }
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  });
}

if (promptInput && tokenCount) {
  const updateCount = () => {
    const words = promptInput.value.trim() ? promptInput.value.trim().split(/\s+/).length : 0;
    tokenCount.textContent = `${words} / 2000 TOKENS`;
  };
  promptInput.addEventListener("input", updateCount);
  updateCount();
}

document.querySelectorAll("[data-radio-group], .engine-stack").forEach((group) => {
  group.addEventListener("change", (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== "radio") return;
    const name = input.name;
    document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`).forEach((radio) => {
      const card = radio.closest(".platform-card, .engine-card, .mode-row");
      if (card) card.classList.toggle("active", radio.checked);
    });
  });
});

if (form && loading) {
  form.addEventListener("submit", () => {
    loading.hidden = false;
  });
}
