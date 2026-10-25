(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const guild = document.querySelector("#guild");
  const channel = document.querySelector("#channel");
  const content = document.querySelector("#content");
  const form = document.querySelector("#composer");
  const alertBox = document.querySelector("#alert");
  const everyone = document.querySelector("#mention-everyone");
  const rolesEnabled = document.querySelector("#mention-roles");
  const usersEnabled = document.querySelector("#mention-users");
  const roles = document.querySelector("#roles");
  const users = document.querySelector("#users");
  let guildData = null;

  const selectedText = (element) => element.selectedOptions[0]?.textContent || "未選択";
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
    if (!response.ok) throw new Error(data.error || "処理に失敗しました。");
    return data;
  };
  const fill = (element, items, placeholder, label) => {
    element.replaceChildren();
    if (placeholder) element.add(new Option(placeholder, ""));
    items.forEach((item) => element.add(new Option(label(item), item.id)));
  };
  const renderPreview = () => {
    const preview = document.querySelector("#preview-message");
    preview.replaceChildren();
    preview.classList.toggle("muted", !content.value);
    if (!content.value) {
      preview.textContent = "メッセージを入力すると、ここにプレビューが表示されます。";
    } else {
      const fragment = document.createDocumentFragment();
      const mentionPattern = /(@everyone|@here|<@!?\d+>|<@&\d+>)/g;
      content.value.split(mentionPattern).forEach((part) => {
        if (mentionPattern.test(part)) {
          const span = document.createElement("span");
          span.className = "mention";
          span.textContent = part;
          fragment.append(span);
        } else {
          fragment.append(document.createTextNode(part));
        }
        mentionPattern.lastIndex = 0;
      });
      preview.append(fragment);
    }
    document.querySelector("#counter").textContent = `${content.value.length} / ${content.maxLength}`;
    document.querySelector("#preview-guild").textContent = selectedText(guild);
    document.querySelector("#preview-channel").textContent = selectedText(channel);
    const enabled = [];
    if (everyone.checked) enabled.push("Everyone/Here");
    if (rolesEnabled.checked) enabled.push(`ロール ${selectedValues(roles).length}件`);
    if (usersEnabled.checked) enabled.push(`ユーザー ${selectedValues(users).length}件`);
    document.querySelector("#preview-mentions").textContent = enabled.join("、") || "なし";
    document.querySelector("#destination").textContent = channel.value
      ? `${selectedText(guild)} の #${selectedText(channel)} に送信します。`
      : "送信先はまだ選択されていません。";
  };

  api("/api/guilds").then((data) => {
    fill(guild, data.guilds, "サーバーを選択", (item) => `${item.name} (${item.id})`);
    document.querySelector(".status-dot").textContent = "Bot接続済み";
  }).catch((error) => showError(error.message));

  guild.addEventListener("change", async () => {
    channel.disabled = true;
    fill(channel, [], "読み込み中…", () => "");
    try {
      guildData = await api(`/api/guilds/${guild.value}/channels`);
      fill(channel, guildData.channels, "チャンネルを選択", (item) => `# ${item.name}`);
      fill(roles, guildData.roles, "", (item) => `@${item.name}${item.mentionable ? "" : " (要権限)"}`);
      fill(users, guildData.users, "", (item) => `@${item.name}`);
      channel.disabled = false;
      clearError();
    } catch (error) {
      showError(error.message);
    }
    renderPreview();
  });
  channel.addEventListener("change", renderPreview);
  content.addEventListener("input", renderPreview);
  [everyone, rolesEnabled, usersEnabled].forEach((input) => input.addEventListener("change", () => {
    roles.disabled = !rolesEnabled.checked;
    users.disabled = !usersEnabled.checked;
    renderPreview();
  }));
  [roles, users].forEach((input) => input.addEventListener("change", renderPreview));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    if (!form.reportValidity()) return;
    const channelInfo = guildData?.channels.find((item) => item.id === channel.value);
    if (everyone.checked && !channelInfo?.can_mention_everyone) {
      showError("このチャンネルではBotにEveryone/Hereの通知権限がありません。");
      return;
    }
    const mentionSummary = document.querySelector("#preview-mentions").textContent;
    const warning = everyone.checked ? "\n\n注意: Everyone/Hereへの通知が有効です。" : "";
    const summary = content.value.length > 120 ? `${content.value.slice(0, 120)}…` : content.value;
    if (!window.confirm(`送信先: ${selectedText(guild)} / #${selectedText(channel)}\n通知: ${mentionSummary}\n\n${summary}${warning}\n\n送信しますか？`)) return;
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "送信中…";
    try {
      const tokenData = await api("/api/send-token", { method: "POST", headers: { "X-CSRF-Token": csrf } });
      const payload = {
        guild_id: guild.value,
        channel_id: channel.value,
        content: content.value,
        send_token: tokenData.send_token,
        mentions: {
          everyone: everyone.checked,
          roles: rolesEnabled.checked ? selectedValues(roles) : [],
          users: usersEnabled.checked ? selectedValues(users) : [],
        },
      };
      const result = await api("/api/announcements", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify(payload),
      });
      window.location.assign(`/history?sent=${encodeURIComponent(result.message_id)}`);
    } catch (error) {
      showError(error.message);
      submit.disabled = false;
      submit.textContent = "内容を確認して送信";
    }
  });
  renderPreview();
})();
