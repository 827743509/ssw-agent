<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import {
  Bot,
  CircleStop,
  Database,
  RotateCcw,
  Send,
  Sparkles,
  Workflow,
} from "@lucide/vue";
import mascotUrl from "./assets/assistant-mascot.png";
import {
  type AgentId,
  getLangGraphApiUrl,
  streamAgentAnswer,
} from "./services/langgraph";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  agent?: AgentId;
  status?: "streaming" | "done" | "error" | "stopped";
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
    content: "你好，我是 SSW Agent。选择一个智能体后直接提问，我会用流式输出回复你。",
    status: "done",
  },
]);

const scrollRef = ref<HTMLElement | null>(null);
const abortController = ref<AbortController | null>(null);

const activeAgent = computed(() => agents.find((agent) => agent.id === selectedAgent.value) ?? agents[0]);
const canSend = computed(() => inputText.value.trim().length > 0 && !isStreaming.value);

function agentLabel(agentId?: AgentId): string {
  return agents.find((agent) => agent.id === agentId)?.label ?? "SSW Agent";
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

  const agentId = selectedAgent.value;
  const assistantMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    agent: agentId,
    content: "",
    status: "streaming",
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
  progressText.value = `${agentLabel(agentId)} 正在思考`;
  abortController.value = new AbortController();
  await scrollToBottom();

  await streamAgentAnswer(agentId, question, abortController.value.signal, {
    onToken(token) {
      assistantMessage.content += token;
      void scrollToBottom();
    },
    onProgress(progress) {
      progressText.value = progress.node
        ? `${progress.node} · ${progress.detail}`
        : progress.detail;
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
  });
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
          <h1>次元问答终端</h1>
        </div>
      </div>

      <div class="mascot-panel">
        <img :src="mascotUrl" alt="SSW Agent 二次元助手" />
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
            <p>{{ message.content }}</p>
            <span v-if="message.status === 'streaming'" class="typing-caret"></span>
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
