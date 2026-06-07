<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  Bot,
  CheckCircle2,
  CircleStop,
  Database,
  Download,
  LoaderCircle,
  Plus,
  RotateCcw,
  Save,
  Send,
  Server,
  Sparkles,
  Trash2,
  Upload,
  Workflow,
  Wrench,
  X,
  Zap,
} from "@lucide/vue";
import mascotUrl from "./assets/assistant-mascot.png";
import {
  type AgentId,
  type ToolCallProgress,
  getLangGraphApiUrl,
  streamAgentAnswer,
} from "./services/langgraph";
import {
  type DataSourceCreate,
  type DataSourceSummary,
  type DataSourceType,
  createDataSource,
  deleteDataSource,
  downloadDataSourceSkill,
  generateDataSourceSkill,
  listDataSources,
  replaceDataSourceSkill,
} from "./services/datasources";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  agent?: AgentId;
  status?: "streaming" | "done" | "error" | "stopped";
  toolCalls?: ToolCallProgress[];
};

const agents: Array<{
  id: AgentId;
  label: string;
  caption: string;
  icon: typeof Workflow;
}> = [
  {
    id: "supervisor",
    label: "Supervisor",
    caption: "任务规划与分发",
    icon: Workflow,
  },
  {
    id: "text_to_sql_agent",
    label: "Text to SQL",
    caption: "自然语言生成 SQL",
    icon: Database,
  },
  {
    id: "default_agent",
    label: "Default Agent",
    caption: "通用技能问答",
    icon: Bot,
  },
];

const selectedAgent = ref<AgentId>("supervisor");
const inputText = ref("");
const isStreaming = ref(false);
const progressText = ref("待命中");
const messages = ref<ChatMessage[]>([
  {
    id: crypto.randomUUID(),
    role: "assistant",
    agent: "supervisor",
    content: "你好，我是 SSW Agent。选择一个智能体后直接提问，我会在等待时展示工具调用过程，并在完成后输出最终回答。",
    status: "done",
  },
]);

const dataSources = ref<DataSourceSummary[]>([]);
const selectedDataSourceId = ref(localStorage.getItem("ssw.selectedDataSource") || "");
const isLoadingDataSources = ref(false);
const isSavingDataSource = ref(false);
const isGeneratingSkill = ref(false);
const isReplacingSkill = ref(false);
const isDeletingDataSource = ref(false);
const showDataSourceForm = ref(false);
const dataSourceError = ref("");
const dataSourceForm = ref<DataSourceCreate>({
  name: "",
  type: "mysql",
  host: "127.0.0.1",
  port: 3306,
  database: "",
  username: "",
  password: "",
  skill_body: "",
});

const scrollRef = ref<HTMLElement | null>(null);
const skillUploadInputRef = ref<HTMLInputElement | null>(null);
const abortController = ref<AbortController | null>(null);

const activeAgent = computed(() => agents.find((agent) => agent.id === selectedAgent.value) ?? agents[0]);
const selectedDataSource = computed(() => (
  dataSources.value.find((source) => source.id === selectedDataSourceId.value) ?? null
));
const canSend = computed(() => {
  if (!inputText.value.trim() || isStreaming.value) {
    return false;
  }

  return selectedAgent.value !== "text_to_sql_agent" || Boolean(selectedDataSource.value);
});
const canGenerateSkill = computed(() => (
  Boolean(dataSourceForm.value.name.trim())
  && Boolean(dataSourceForm.value.host.trim())
  && Boolean(dataSourceForm.value.database.trim())
  && Boolean(dataSourceForm.value.username.trim())
  && dataSourceForm.value.port > 0
  && !isGeneratingSkill.value
));
const canSaveDataSource = computed(() => (
  Boolean(dataSourceForm.value.skill_body.trim())
  && !isSavingDataSource.value
  && !isGeneratingSkill.value
));

watch(selectedDataSourceId, (value) => {
  if (value) {
    localStorage.setItem("ssw.selectedDataSource", value);
  } else {
    localStorage.removeItem("ssw.selectedDataSource");
  }
});

watch(() => dataSourceForm.value.type, (type) => {
  dataSourceForm.value.port = type === "mysql" ? 3306 : 8123;
});

onMounted(() => {
  void refreshDataSources();
});

function agentLabel(agentId?: AgentId): string {
  return agents.find((agent) => agent.id === agentId)?.label ?? "SSW Agent";
}

function dataSourceTypeLabel(type: DataSourceType): string {
  return type === "mysql" ? "MySQL" : "ClickHouse";
}

function buildTextToSqlContext(): string | undefined {
  if (selectedAgent.value !== "text_to_sql_agent" || !selectedDataSource.value) {
    return undefined;
  }

  const source = selectedDataSource.value;
  return [
    "当前 Text to SQL 数据源：",
    `- 名称：${source.name}`,
    `- 类型：${dataSourceTypeLabel(source.type)}`,
    `- Host：${source.host}`,
    `- Port：${source.port}`,
    `- Database：${source.database}`,
    `- Skill：${source.skill_path}`,
    "",
    `请优先读取并使用该数据源对应的 skill 文档，生成 ${dataSourceTypeLabel(source.type)} 方言的只读查询 SQL。`,
  ].join("\n");
}

async function refreshDataSources(): Promise<void> {
  isLoadingDataSources.value = true;
  dataSourceError.value = "";

  try {
    dataSources.value = await listDataSources();
    if (selectedDataSourceId.value && !selectedDataSource.value) {
      selectedDataSourceId.value = "";
    }
    if (!selectedDataSourceId.value && dataSources.value.length) {
      selectedDataSourceId.value = dataSources.value[0].id;
    }
  } catch (error) {
    dataSourceError.value = error instanceof Error ? error.message : "加载数据源失败";
  } finally {
    isLoadingDataSources.value = false;
  }
}

function resetDataSourceForm(): void {
  dataSourceForm.value = {
    name: "",
    type: "mysql",
    host: "127.0.0.1",
    port: 3306,
    database: "",
    username: "",
    password: "",
    skill_body: "",
  };
  dataSourceError.value = "";
}

async function generateSkill(): Promise<void> {
  dataSourceError.value = "";
  isGeneratingSkill.value = true;

  try {
    const generated = await generateDataSourceSkill({
      name: dataSourceForm.value.name,
      type: dataSourceForm.value.type,
      host: dataSourceForm.value.host,
      port: dataSourceForm.value.port,
      database: dataSourceForm.value.database,
      username: dataSourceForm.value.username,
      password: dataSourceForm.value.password,
    });
    dataSourceForm.value.skill_body = generated.skill_body;
    dataSourceError.value = `已生成 ${generated.table_count} 张表、${generated.column_count} 个字段的 Skill 文档，可继续编辑。`;
  } catch (error) {
    dataSourceError.value = error instanceof Error ? error.message : "生成 Skill 失败";
  } finally {
    isGeneratingSkill.value = false;
  }
}

async function saveDataSource(): Promise<void> {
  dataSourceError.value = "";
  isSavingDataSource.value = true;

  try {
    const created = await createDataSource(dataSourceForm.value);
    dataSources.value = [
      ...dataSources.value.filter((source) => source.id !== created.id),
      created,
    ];
    selectedDataSourceId.value = created.id;
    showDataSourceForm.value = false;
    resetDataSourceForm();
  } catch (error) {
    dataSourceError.value = error instanceof Error ? error.message : "创建数据源失败";
  } finally {
    isSavingDataSource.value = false;
  }
}

async function downloadSelectedDataSourceSkill(): Promise<void> {
  if (!selectedDataSource.value) {
    return;
  }

  dataSourceError.value = "";
  try {
    const source = selectedDataSource.value;
    const blob = await downloadDataSourceSkill(source.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${source.id}-SKILL.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    dataSourceError.value = error instanceof Error ? error.message : "下载 Skill 失败";
  }
}

function openSkillUploadPicker(): void {
  skillUploadInputRef.value?.click();
}

async function replaceSelectedDataSourceSkill(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || !selectedDataSource.value) {
    input.value = "";
    return;
  }

  dataSourceError.value = "";
  isReplacingSkill.value = true;
  try {
    const updated = await replaceDataSourceSkill(selectedDataSource.value.id, file);
    dataSources.value = dataSources.value.map((source) => (
      source.id === updated.id ? updated : source
    ));
    selectedDataSourceId.value = updated.id;
    dataSourceError.value = "已替换当前数据源的 Skill 文档。";
  } catch (error) {
    dataSourceError.value = error instanceof Error ? error.message : "替换 Skill 失败";
  } finally {
    isReplacingSkill.value = false;
    input.value = "";
  }
}

async function deleteSelectedDataSource(): Promise<void> {
  if (!selectedDataSource.value || isDeletingDataSource.value) {
    return;
  }

  const source = selectedDataSource.value;
  if (!window.confirm(`确认删除数据源「${source.name}」？该操作会删除对应的 SKILL.md 文件。`)) {
    return;
  }

  dataSourceError.value = "";
  isDeletingDataSource.value = true;
  try {
    await deleteDataSource(source.id);
    const remaining = dataSources.value.filter((item) => item.id !== source.id);
    dataSources.value = remaining;
    selectedDataSourceId.value = remaining[0]?.id ?? "";
    dataSourceError.value = "已删除数据源。";
  } catch (error) {
    dataSourceError.value = error instanceof Error ? error.message : "删除数据源失败";
  } finally {
    isDeletingDataSource.value = false;
  }
}

async function scrollToBottom(): Promise<void> {
  await nextTick();
  const el = scrollRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

function resetChat(): void {
  if (isStreaming.value) {
    stopStreaming();
  }

  messages.value = [];
  progressText.value = "已清空";
}

function upsertToolCall(message: ChatMessage, toolCall: ToolCallProgress): void {
  const toolCalls = message.toolCalls ?? [];
  const existing = toolCalls.find((item) => item.id === toolCall.id);

  if (existing) {
    existing.name = toolCall.name;
    existing.node = toolCall.node || existing.node;
    existing.status = toolCall.status;
  } else {
    toolCalls.push(toolCall);
  }

  message.toolCalls = toolCalls;
}

function stopStreaming(): void {
  abortController.value?.abort();
  const lastAssistant = [...messages.value].reverse().find((message) => message.role === "assistant");
  if (lastAssistant?.status === "streaming") {
    lastAssistant.status = "stopped";
    if (!lastAssistant.content.trim()) {
      lastAssistant.content = "已停止生成。";
    }
  }
  isStreaming.value = false;
  progressText.value = "已停止";
}

async function sendMessage(): Promise<void> {
  const question = inputText.value.trim();
  if (!question || isStreaming.value) {
    return;
  }

  if (selectedAgent.value === "text_to_sql_agent" && !selectedDataSource.value) {
    messages.value.push({
      id: crypto.randomUUID(),
      role: "assistant",
      agent: "text_to_sql_agent",
      content: "请先在左侧添加并选择一个数据源。",
      status: "error",
    });
    await scrollToBottom();
    return;
  }

  const agentId = selectedAgent.value;
  const assistantMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    agent: agentId,
    content: "",
    status: "streaming",
    toolCalls: [],
  };

  messages.value.push({
    id: crypto.randomUUID(),
    role: "user",
    content: question,
    status: "done",
  });
  messages.value.push(assistantMessage);

  inputText.value = "";
  isStreaming.value = true;
  progressText.value = `${agentLabel(agentId)} 正在处理`;
  abortController.value = new AbortController();
  await scrollToBottom();

  await streamAgentAnswer(agentId, question, abortController.value.signal, {
    onToolCall(toolCall) {
      upsertToolCall(assistantMessage, toolCall);
      void scrollToBottom();
    },
    onProgress(progress) {
      progressText.value = progress.node
        ? `${progress.node} · ${progress.detail}`
        : progress.detail;
    },
    onFinal(content) {
      assistantMessage.content = content || "本次运行没有返回最终文本。";
      void scrollToBottom();
    },
    onDone() {
      if (assistantMessage.status === "streaming") {
        assistantMessage.status = "done";
      }
      isStreaming.value = false;
      progressText.value = "回复完成";
      abortController.value = null;
      void scrollToBottom();
    },
    onError(message) {
      assistantMessage.status = "error";
      assistantMessage.content = assistantMessage.content
        ? `${assistantMessage.content}\n\n请求失败：${message}`
        : `请求失败：${message}`;
      isStreaming.value = false;
      progressText.value = "请求失败";
      abortController.value = null;
      void scrollToBottom();
    },
  }, buildTextToSqlContext());
}

function handleKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    void sendMessage();
  }
}
</script>

<template>
  <main class="app-shell">
    <section class="sidebar" aria-label="智能体控制台">
      <div class="brand">
        <div class="brand-mark">
          <Sparkles :size="22" />
        </div>
        <div>
          <p class="eyebrow">SSW Agent</p>
          <h1>盐汽水问答终端</h1>
        </div>
      </div>

      <div class="mascot-panel">
        <img :src="mascotUrl" alt="SSW Agent 助手形象" />
      </div>

      <div class="agent-panel">
        <p class="panel-title">选择智能体</p>
        <div class="agent-list">
          <button
            v-for="agent in agents"
            :key="agent.id"
            class="agent-option"
            :class="{ active: selectedAgent === agent.id }"
            type="button"
            @click="selectedAgent = agent.id"
          >
            <component :is="agent.icon" :size="19" />
            <span>
              <strong>{{ agent.label }}</strong>
              <small>{{ agent.caption }}</small>
            </span>
          </button>
        </div>
      </div>

      <section v-if="selectedAgent === 'text_to_sql_agent'" class="datasource-panel">
        <div class="panel-heading">
          <p class="panel-title">数据源</p>
          <button
            class="mini-icon-button"
            type="button"
            title="添加数据源"
            @click="showDataSourceForm = !showDataSourceForm"
          >
            <X v-if="showDataSourceForm" :size="16" />
            <Plus v-else :size="16" />
          </button>
        </div>

        <label class="field-label">
          <span>当前数据源</span>
          <select v-model="selectedDataSourceId" :disabled="isLoadingDataSources || !dataSources.length">
            <option value="">未选择</option>
            <option v-for="source in dataSources" :key="source.id" :value="source.id">
              {{ source.name }} · {{ dataSourceTypeLabel(source.type) }}
            </option>
          </select>
        </label>

        <div v-if="selectedDataSource" class="datasource-summary">
          <Server :size="16" />
          <span>{{ selectedDataSource.host }}:{{ selectedDataSource.port }}/{{ selectedDataSource.database }}</span>
        </div>

        <div v-if="selectedDataSource" class="datasource-actions">
          <button class="secondary-button" type="button" @click="downloadSelectedDataSourceSkill">
            <Download :size="16" />
            下载 SKILL.md
          </button>
          <button
            class="secondary-button"
            type="button"
            :disabled="isReplacingSkill"
            @click="openSkillUploadPicker"
          >
            <Upload :size="16" />
            {{ isReplacingSkill ? "替换中" : "上传替换" }}
          </button>
          <button
            class="secondary-button danger"
            type="button"
            :disabled="isDeletingDataSource"
            @click="deleteSelectedDataSource"
          >
            <Trash2 :size="16" />
            {{ isDeletingDataSource ? "删除中" : "删除数据源" }}
          </button>
          <input
            ref="skillUploadInputRef"
            class="visually-hidden"
            type="file"
            accept=".md,text/markdown,text/plain"
            @change="replaceSelectedDataSourceSkill"
          />
        </div>

        <form v-if="showDataSourceForm" class="datasource-form" @submit.prevent="saveDataSource">
          <label class="field-label">
            <span>名称</span>
            <input v-model.trim="dataSourceForm.name" required placeholder="blog_prod" />
          </label>
          <label class="field-label">
            <span>类型</span>
            <select v-model="dataSourceForm.type">
              <option value="mysql">MySQL</option>
              <option value="clickhouse">ClickHouse</option>
            </select>
          </label>
          <div class="field-grid">
            <label class="field-label">
              <span>Host</span>
              <input v-model.trim="dataSourceForm.host" required />
            </label>
            <label class="field-label">
              <span>Port</span>
              <input v-model.number="dataSourceForm.port" required type="number" min="1" max="65535" />
            </label>
          </div>
          <label class="field-label">
            <span>Database</span>
            <input v-model.trim="dataSourceForm.database" required />
          </label>
          <div class="field-grid">
            <label class="field-label">
              <span>Username</span>
              <input v-model.trim="dataSourceForm.username" required />
            </label>
            <label class="field-label">
              <span>Password</span>
              <input v-model="dataSourceForm.password" type="password" autocomplete="new-password" />
            </label>
          </div>
          <div class="form-actions">
            <button class="secondary-button" type="button" :disabled="!canGenerateSkill" @click="generateSkill">
              <Zap :size="16" />
              {{ isGeneratingSkill ? "生成中" : "连接并生成" }}
            </button>
          </div>
          <label class="field-label">
            <span>Skill 文档</span>
            <textarea
              v-model="dataSourceForm.skill_body"
              required
              rows="8"
              placeholder="点击连接并生成，或手动填写 Skill Markdown 正文"
            />
          </label>
          <button class="secondary-button" type="submit" :disabled="!canSaveDataSource">
            <Save :size="16" />
            {{ isSavingDataSource ? "保存中" : "保存 Skill" }}
          </button>
        </form>

        <p v-if="dataSourceError" class="inline-error">{{ dataSourceError }}</p>
      </section>

      <div class="status-card">
        <span class="pulse-dot" :class="{ streaming: isStreaming }"></span>
        <div>
          <strong>{{ progressText }}</strong>
          <small>{{ getLangGraphApiUrl() }}</small>
        </div>
      </div>
    </section>

    <section class="chat-workspace" aria-label="问答聊天区">
      <header class="chat-header">
        <div>
          <p class="eyebrow">当前模式</p>
          <h2>{{ activeAgent.label }}</h2>
        </div>
        <button class="icon-button" type="button" title="清空对话" @click="resetChat">
          <RotateCcw :size="20" />
        </button>
      </header>

      <div ref="scrollRef" class="message-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="message.role"
        >
          <div class="avatar">
            <Bot v-if="message.role === 'assistant'" :size="18" />
            <span v-else>你</span>
          </div>
          <div class="bubble" :class="message.status">
            <div v-if="message.role === 'assistant'" class="bubble-meta">
              {{ agentLabel(message.agent) }}
            </div>

            <div
              v-if="message.role === 'assistant' && message.status === 'streaming'"
              class="tool-progress"
            >
              <div v-if="!message.toolCalls?.length" class="tool-row running">
                <LoaderCircle :size="16" />
                <span>模型正在处理</span>
              </div>
              <div
                v-for="tool in message.toolCalls"
                :key="tool.id"
                class="tool-row"
                :class="tool.status"
              >
                <LoaderCircle v-if="tool.status === 'running'" :size="16" />
                <CheckCircle2 v-else-if="tool.status === 'done'" :size="16" />
                <Wrench v-else :size="16" />
                <span>{{ tool.name }}</span>
                <small v-if="tool.node">{{ tool.node }}</small>
              </div>
            </div>

            <p v-if="message.content">{{ message.content }}</p>
          </div>
        </article>
      </div>

      <form class="composer" @submit.prevent="sendMessage">
        <textarea
          v-model="inputText"
          rows="3"
          placeholder="输入问题，Ctrl + Enter 发送"
          :disabled="isStreaming"
          @keydown="handleKeydown"
        ></textarea>
        <div class="composer-actions">
          <span>{{ activeAgent.caption }}</span>
          <button
            v-if="isStreaming"
            class="send-button stop"
            type="button"
            @click="stopStreaming"
          >
            <CircleStop :size="20" />
            停止
          </button>
          <button v-else class="send-button" type="submit" :disabled="!canSend">
            <Send :size="20" />
            发送
          </button>
        </div>
      </form>
    </section>
  </main>
</template>
