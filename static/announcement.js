(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const guilds = document.querySelector("#guilds");
  const destinationsRoot = document.querySelector("#destinations");
  const commonMessage = document.querySelector("#common-message");
  const content = document.querySelector("#content");
  const form = document.querySelector("#composer");
  const alertBox = document.querySelector("#alert");
  const guildDetails = new Map();
  const selectedValues = (element) => [...element.selectedOptions].map((option) => option.value);
  const messageMode = () => document.querySelector('input[name="message-mode"]:checked').value;
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
  const makeSelect = (items, label) => {
    const select = document.createElement("select");
    select.multiple = true;
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
  const makeChannelList = (channels) => {
    const list = document.createElement("div");
    list.className = "channel-check-list";
    channels.forEach((channel) => {
      const label = document.createElement("label");
      label.className = "channel-check";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = channel.id;
      input.dataset.channelName = channel.name;
      input.addEventListener("change", () => { updateSeparateMessages(); renderPreview(); });
      label.append(input, document.createTextNode(`# ${channel.name}`));
      list.append(label);
    });
    return list;
  };
  const createDestinationCard = (data) => {
    const card = document.createElement("section");
    card.className = "destination-card";
    card.dataset.guildId = data.guild.id;
    const title = document.createElement("h3");
    title.textContent = data.guild.name;
    const channelLabel = document.createElement("div");
    channelLabel.className = "section-label";
    channelLabel.textContent = "送信チャンネル（複数選択可）";
    const channelList = makeChannelList(data.channels);
    const messages = document.createElement("div");
    messages.className = "separate-messages hidden";
    const fieldset = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = "通知を許可するメンション";
    const note = document.createElement("p");
    note.className = "field-note";
    note.textContent = "このサーバーで選択した全チャンネルに適用されます。";
    const everyone = makeToggle("Everyone / Here");
    everyone.input.className = "destination-everyone";
    const roleToggle = makeToggle("ロール");
    const roleSelect = makeSelect(data.roles, (item) => `@${item.name}${item.mentionable ? "" : " (要権限)"}`);
    roleSelect.className = "destination-roles";
    roleSelect.disabled = true;
    roleToggle.input.addEventListener("change", () => { roleSelect.disabled = !roleToggle.input.checked; renderPreview(); });
    const userToggle = makeToggle("ユーザー");
    const userSelect = makeSelect(data.users, (item) => `@${item.name}`);
    userSelect.className = "destination-users";
    userSelect.disabled = true;
    userToggle.input.addEventListener("change", () => { userSelect.disabled = !userToggle.input.checked; renderPreview(); });
    [everyone.input, roleSelect, userSelect].forEach((element) => element.addEventListener("change", renderPreview));
    fieldset.append(legend, note, everyone.label, roleToggle.label, roleSelect, userToggle.label, userSelect);
    card.append(title, channelLabel, channelList, messages, fieldset);
    return card;
  };
  const updateSeparateMessages = () => {
    const separate = messageMode() === "separate";
    commonMessage.classList.toggle("hidden", separate);
    content.required = !separate;
    destinationsRoot.querySelectorAll(".destination-card").forEach((card) => {
      const container = card.querySelector(".separate-messages");
      container.classList.toggle("hidden", !separate);
      const checked = [...card.querySelectorAll('.channel-check input:checked')];
      const existing = new Map([...container.querySelectorAll(".channel-message")].map((item) => [item.dataset.channelId, item]));
      container.replaceChildren();
      checked.forEach((channel) => {
        let field = existing.get(channel.value);
        if (!field) {
          field = document.createElement("div");
          field.className = "channel-message";
          field.dataset.channelId = channel.value;
          const label = document.createElement("label");
          label.textContent = `# ${channel.dataset.channelName} のメッセージ`;
          const textarea = document.createElement("textarea");
          textarea.maxLength = 2000;
          textarea.rows = 5;
          textarea.placeholder = "このチャンネルへ送るメッセージを入力";
          textarea.addEventListener("input", renderPreview);
          field.append(label, textarea);
        }
        field.querySelector("textarea").required = separate;
        container.append(field);
      });
    });
    renderPreview();
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
    updateSeparateMessages();
  };
  const collectDestinations = () => {
    const separate = messageMode() === "separate";
    return [...destinationsRoot.querySelectorAll(".destination-card")].flatMap((card) => {
      const mentions = {
        everyone: card.querySelector(".destination-everyone").checked,
        roles: card.querySelector(".destination-roles").disabled ? [] : selectedValues(card.querySelector(".destination-roles")),
        users: card.querySelector(".destination-users").disabled ? [] : selectedValues(card.querySelector(".destination-users")),
      };
      return [...card.querySelectorAll('.channel-check input:checked')].map((channel) => ({
        guild_id: card.dataset.guildId,
        channel_id: channel.value,
        channel_name: channel.dataset.channelName,
        content: separate ? card.querySelector(`.channel-message[data-channel-id="${channel.value}"] textarea`).value : content.value,
        mentions,
      }));
    });
  };
  const renderPreview = () => {
    const destinations = collectDestinations();
    const firstMessage = destinations[0]?.content || (messageMode() === "same" ? content.value : "");
    const preview = document.querySelector("#preview-message");
    preview.replaceChildren();
    preview.classList.toggle("muted", !firstMessage);
    preview.textContent = firstMessage || "送信先とメッセージを入力すると、ここに先頭のプレビューが表示されます。";
    document.querySelector("#counter").textContent = `${content.value.length} / ${content.maxLength}`;
    document.querySelector("#preview-destinations").textContent = destinations.length
      ? destinations.map((item) => `${guildDetails.get(item.guild_id).guild.name} / #${item.channel_name}`).join("、")
      : "未選択";
    const mentions = destinations.reduce((count, item) => count + Number(item.mentions.everyone) + item.mentions.roles.length + item.mentions.users.length, 0);
    document.querySelector("#preview-mentions").textContent = mentions ? `${mentions}設定` : "なし";
  };
  api("/api/guilds").then(({ data }) => {
    fill(guilds, data.guilds, (item) => `${item.name} (${item.id})`);
    document.querySelector(".status-dot").textContent = "Bot接続済み";
  }).catch((error) => showError(error.message));
  guilds.addEventListener("change", renderDestinations);
  content.addEventListener("input", renderPreview);
  document.querySelectorAll('input[name="message-mode"]').forEach((input) => input.addEventListener("change", updateSeparateMessages));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    const destinations = collectDestinations();
    if (!destinations.length) {
      showError("送信するチャンネルを1件以上選択してください。");
      return;
    }
    if (destinations.length > 50) {
      showError("一度に送信できるチャンネルは最大50件です。");
      return;
    }
    if (destinations.some((item) => !item.content.trim())) {
      showError("すべての送信先にメッセージを入力してください。");
      return;
    }
    for (const destination of destinations) {
      const data = guildDetails.get(destination.guild_id);
      const channel = data.channels.find((item) => item.id === destination.channel_id);
      if (destination.mentions.everyone && !channel?.can_mention_everyone) {
        showError(`${data.guild.name} / #${destination.channel_name}ではEveryone/Hereを通知できません。`);
        return;
      }
      if (destination.mentions.everyone && !destination.content.includes("@everyone") && !destination.content.includes("@here")) {
        showError(`${data.guild.name} / #${destination.channel_name}の本文にEveryone/Hereメンションがありません。`);
        return;
      }
    }
    const names = destinations.map((item) => `${guildDetails.get(item.guild_id).guild.name} / #${item.channel_name}`);
    const warning = destinations.some((item) => item.mentions.everyone) ? "\n\n注意: Everyone/Hereへの通知を含みます。" : "";
    if (!window.confirm(`${destinations.length}チャンネルへ送信します。\n\n${names.join("\n")}${warning}\n\n送信しますか？`)) return;
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "一括送信中…";
    try {
      const token = (await api("/api/send-token", { method: "POST", headers: { "X-CSRF-Token": csrf } })).data.send_token;
      const response = await api("/api/announcements", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ send_token: token, destinations }),
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
