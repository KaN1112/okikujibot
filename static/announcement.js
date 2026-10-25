(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const guilds = document.querySelector("#guilds");
  const destinationsRoot = document.querySelector("#destinations");
  const content = document.querySelector("#content");
  const form = document.querySelector("#composer");
  const alertBox = document.querySelector("#alert");
  const guildDetails = new Map();
  const selectedValues = (element) => [...element.selectedOptions].map((option) => option.value);
  const showError = (message) => {
    alertBox.textContent = message;
    alertBox.classList.remove("hidden");
    alertBox.scrollIntoView({ behavior: "smooth", block: "center" });
  };
  const clearError = () => alertBox.classList.add("hidden");
  const api = async (url, options = {}) => {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok && response.status !== 207) throw new Error(data.error || "処理に失敗しました。");
    return { data, status: response.status };
  };
  const fill = (element, items, label) => {
    element.replaceChildren();
    items.forEach((item) => element.add(new Option(label(item), item.id)));
  };
  const makeSelect = (items, multiple, label) => {
    const select = document.createElement("select");
    select.multiple = multiple;
    if (!multiple) select.add(new Option("チャンネルを選択", ""));
    items.forEach((item) => select.add(new Option(label(item), item.id)));
    return select;
  };
  const makeToggle = (text) => {
    const label = document.createElement("label");
    label.className = "toggle";
    const input = document.createElement("input");
    input.type = "checkbox";
    label.append(input, document.createElement("span"), document.createTextNode(text));
    return { label, input };
  };
  const createDestinationCard = (data) => {
    const card = document.createElement("section");
    card.className = "destination-card";
    card.dataset.guildId = data.guild.id;
    const title = document.createElement("h3");
    title.textContent = data.guild.name;
    const channelLabel = document.createElement("label");
    channelLabel.textContent = "送信チャンネル";
    const channel = makeSelect(data.channels, false, (item) => `# ${item.name}`);
    channel.className = "destination-channel";
    channel.required = true;
    const fieldset = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = "通知を許可するメンション";
    const note = document.createElement("p");
    note.className = "field-note";
    note.textContent = "このサーバーで通知する対象だけをONにしてください。";
    const everyone = makeToggle("Everyone / Here");
    everyone.input.className = "destination-everyone";
    const roleToggle = makeToggle("ロール");
    const roleSelect = makeSelect(data.roles, true, (item) => `@${item.name}${item.mentionable ? "" : " (要権限)"}`);
    roleSelect.className = "destination-roles";
    roleSelect.disabled = true;
    roleToggle.input.addEventListener("change", () => { roleSelect.disabled = !roleToggle.input.checked; renderPreview(); });
    const userToggle = makeToggle("ユーザー");
    const userSelect = makeSelect(data.users, true, (item) => `@${item.name}`);
    userSelect.className = "destination-users";
    userSelect.disabled = true;
    userToggle.input.addEventListener("change", () => { userSelect.disabled = !userToggle.input.checked; renderPreview(); });
    [channel, everyone.input, roleSelect, userSelect].forEach((element) => element.addEventListener("change", renderPreview));
    fieldset.append(legend, note, everyone.label, roleToggle.label, roleSelect, userToggle.label, userSelect);
    card.append(title, channelLabel, channel, fieldset);
    return card;
  };
  const renderDestinations = async () => {
    const chosen = selectedValues(guilds);
    if (chosen.length > 10) {
      [...guilds.options].forEach((option) => { option.selected = chosen.slice(0, 10).includes(option.value); });
      showError("送信先サーバーは最大10件です。");
      return;
    }
    destinationsRoot.replaceChildren();
    try {
      for (const guildId of chosen) {
        if (!guildDetails.has(guildId)) {
          const response = await api(`/api/guilds/${guildId}/channels`);
          guildDetails.set(guildId, response.data);
        }
        destinationsRoot.append(createDestinationCard(guildDetails.get(guildId)));
      }
      clearError();
    } catch (error) { showError(error.message); }
    renderPreview();
  };
  const collectDestinations = () => [...destinationsRoot.querySelectorAll(".destination-card")].map((card) => ({
    guild_id: card.dataset.guildId,
    channel_id: card.querySelector(".destination-channel").value,
    mentions: {
      everyone: card.querySelector(".destination-everyone").checked,
      roles: card.querySelector(".destination-roles").disabled ? [] : selectedValues(card.querySelector(".destination-roles")),
      users: card.querySelector(".destination-users").disabled ? [] : selectedValues(card.querySelector(".destination-users")),
    },
  }));
  const renderPreview = () => {
    const preview = document.querySelector("#preview-message");
    preview.replaceChildren();
    preview.classList.toggle("muted", !content.value);
    if (!content.value) preview.textContent = "メッセージを入力すると、ここにプレビューが表示されます。";
    else {
      const fragment = document.createDocumentFragment();
      const pattern = /(@everyone|@here|<@!?\d+>|<@&\d+>)/g;
      content.value.split(pattern).forEach((part) => {
        if (/^(@everyone|@here|<@!?\d+>|<@&\d+>)$/.test(part)) {
          const span = document.createElement("span");
          span.className = "mention";
          span.textContent = part;
          fragment.append(span);
        } else fragment.append(document.createTextNode(part));
      });
      preview.append(fragment);
    }
    document.querySelector("#counter").textContent = `${content.value.length} / ${content.maxLength}`;
    const cards = [...destinationsRoot.querySelectorAll(".destination-card")];
    document.querySelector("#preview-destinations").textContent = cards.length ? cards.map((card) => `${card.querySelector("h3").textContent} / ${card.querySelector(".destination-channel").selectedOptions[0]?.textContent || "未選択"}`).join("、") : "未選択";
    const mentions = collectDestinations().reduce((count, item) => count + Number(item.mentions.everyone) + item.mentions.roles.length + item.mentions.users.length, 0);
    document.querySelector("#preview-mentions").textContent = mentions ? `${mentions}設定` : "なし";
  };
  api("/api/guilds").then(({ data }) => {
    fill(guilds, data.guilds, (item) => `${item.name} (${item.id})`);
    document.querySelector(".status-dot").textContent = "Bot接続済み";
  }).catch((error) => showError(error.message));
  guilds.addEventListener("change", renderDestinations);
  content.addEventListener("input", renderPreview);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    const destinations = collectDestinations();
    if (!destinations.length || destinations.some((item) => !item.channel_id)) {
      showError("すべてのサーバーで送信チャンネルを選択してください。");
      return;
    }
    for (const destination of destinations) {
      const data = guildDetails.get(destination.guild_id);
      const channel = data.channels.find((item) => item.id === destination.channel_id);
      if (destination.mentions.everyone && !channel?.can_mention_everyone) {
        showError(`${data.guild.name}ではBotにEveryone/Hereの通知権限がありません。`);
        return;
      }
      if (destination.mentions.everyone && !content.value.includes("@everyone") && !content.value.includes("@here")) {
        showError("Everyone/Here設定に対応するメンションが本文にありません。");
        return;
      }
    }
    const names = [...destinationsRoot.querySelectorAll(".destination-card")].map((card) => `${card.querySelector("h3").textContent} / ${card.querySelector(".destination-channel").selectedOptions[0].textContent}`);
    const warning = destinations.some((item) => item.mentions.everyone) ? "\n\n注意: Everyone/Hereへの通知を含みます。" : "";
    if (!window.confirm(`${destinations.length}件へ一括送信します。\n\n${names.join("\n")}${warning}\n\n送信しますか？`)) return;
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "一括送信中…";
    try {
      const token = (await api("/api/send-token", { method: "POST", headers: { "X-CSRF-Token": csrf } })).data.send_token;
      const response = await api("/api/announcements", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ content: content.value, send_token: token, destinations }),
      });
      if (response.data.failure_count) {
        showError(`${response.data.success_count}件成功、${response.data.failure_count}件失敗しました。送信履歴を確認してください。`);
        submit.disabled = false;
        submit.textContent = "内容を確認して送信";
      } else window.location.assign("/history?sent=batch");
    } catch (error) {
      showError(error.message);
      submit.disabled = false;
      submit.textContent = "内容を確認して送信";
    }
  });
  renderPreview();
})();
