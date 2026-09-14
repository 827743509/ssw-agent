<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FileText,
  LoaderCircle,
  RefreshCcw,
  RotateCcw,
  Trash2,
  UploadCloud,
} from "@lucide/vue";
import {
  type DocumentStatus,
  type RagDocument,
  deleteDocument,
  listDocuments,
  retryDocument,
  uploadDocument,
} from "../services/documents";

const pageSize = 20;
const maxUploadBytes = 50 * 1024 * 1024;
const supportedSuffixes = [".pdf", ".docx", ".md", ".markdown", ".html", ".htm"];
const processingStatuses: DocumentStatus[] = ["uploading", "parsing", "indexing"];

const documents = ref<RagDocument[]>([]);
const total = ref(0);
const page = ref(1);
const isLoading = ref(false);
const isUploading = ref(false);
const isDragging = ref(false);
const activeDocumentId = ref<string | null>(null);
const errorText = ref("");
const successText = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
let pollTimer: number | undefined;
let isDisposed = false;

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const hasProcessingDocument = computed(() => (
  documents.value.some((document) => processingStatuses.includes(document.status))
));

onMounted(() => {
  void refreshDocuments();
});

onBeforeUnmount(() => {
  isDisposed = true;
  window.clearTimeout(pollTimer);
});

function schedulePolling(): void {
  window.clearTimeout(pollTimer);
  if (!isDisposed && hasProcessingDocument.value) {
    pollTimer = window.setTimeout(() => {
      void refreshDocuments(true);
    }, 3000);
  }
}

async function refreshDocuments(silent = false): Promise<void> {
  if (!silent) {
    isLoading.value = true;
  }
  errorText.value = "";
  try {
    const result = await listDocuments(page.value, pageSize);
    documents.value = result.items;
    total.value = result.total;
    if (page.value > pageCount.value) {
      page.value = pageCount.value;
      await refreshDocuments(true);
      return;
    }
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "加载文档失败";
  } finally {
    if (!silent) {
      isLoading.value = false;
    }
    schedulePolling();
  }
}

function openFilePicker(): void {
  if (!isUploading.value) {
    fileInput.value?.click();
  }
}

function validateFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  if (!supportedSuffixes.some((suffix) => lowerName.endsWith(suffix))) {
    return "仅支持 PDF、DOCX、Markdown 和 HTML 文档";
  }
  if (file.size === 0) {
    return "不能上传空文件";
  }
  if (file.size > maxUploadBytes) {
    return "文件不能超过 50 MB";
  }
  return null;
}

async function submitFile(file: File): Promise<void> {
  const validationError = validateFile(file);
  if (validationError) {
    errorText.value = validationError;
    return;
  }

  isUploading.value = true;
  errorText.value = "";
  successText.value = "";
  try {
    const document = await uploadDocument(file);
    successText.value = `「${document.name}」已上传，正在解析并写入向量库`;
    page.value = 1;
    await refreshDocuments(true);
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "上传文档失败";
  } finally {
    isUploading.value = false;
    if (fileInput.value) {
      fileInput.value.value = "";
    }
  }
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    void submitFile(file);
  }
}

function handleDrop(event: DragEvent): void {
  isDragging.value = false;
  const file = event.dataTransfer?.files[0];
  if (file) {
    void submitFile(file);
  }
}

async function removeDocument(document: RagDocument): Promise<void> {
  if (!window.confirm(`确认删除文档「${document.name}」及其向量数据吗？`)) {
    return;
  }

  activeDocumentId.value = document.id;
  errorText.value = "";
  successText.value = "";
  try {
    await deleteDocument(document.id);
    successText.value = "文档及其向量数据已删除";
    await refreshDocuments(true);
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "删除文档失败";
  } finally {
    activeDocumentId.value = null;
  }
}

async function retry(document: RagDocument): Promise<void> {
  activeDocumentId.value = document.id;
  errorText.value = "";
  successText.value = "";
  try {
    await retryDocument(document.id);
    successText.value = `已重新提交「${document.name}」`;
    await refreshDocuments(true);
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "重试文档失败";
  } finally {
    activeDocumentId.value = null;
  }
}

async function goToPage(nextPage: number): Promise<void> {
  if (nextPage < 1 || nextPage > pageCount.value || nextPage === page.value) {
    return;
  }
  page.value = nextPage;
  await refreshDocuments();
}

function statusLabel(status: DocumentStatus): string {
  return {
    uploading: "等待处理",
    parsing: "解析中",
    indexing: "向量化中",
    ready: "已入库",
    failed: "处理失败",
  }[status];
}

function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function canDelete(document: RagDocument): boolean {
  return ["uploading", "ready", "failed"].includes(document.status);
}
</script>

<template>
  <section class="manager-page document-manager" aria-label="RAG 文档管理">
    <header class="manager-header">
      <div>
        <p class="eyebrow">RAG Knowledge Base</p>
        <h2>文档管理</h2>
      </div>
      <div class="manager-actions">
        <button
          class="icon-button"
          type="button"
          title="刷新文档"
          :disabled="isLoading"
          @click="refreshDocuments()"
        >
          <RefreshCcw :size="19" :class="{ spinning: isLoading }" />
        </button>
        <button
          class="document-upload-button"
          type="button"
          :disabled="isUploading"
          @click="openFilePicker"
        >
          <LoaderCircle v-if="isUploading" :size="18" class="spinning" />
          <UploadCloud v-else :size="18" />
          {{ isUploading ? "上传中" : "上传文档" }}
        </button>
        <input
          ref="fileInput"
          hidden
          type="file"
          accept=".pdf,.docx,.md,.markdown,.html,.htm,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/html"
          @change="handleFileChange"
        />
      </div>
    </header>

    <button
      class="document-dropzone"
      :class="{ dragging: isDragging }"
      type="button"
      :disabled="isUploading"
      @click="openFilePicker"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <UploadCloud :size="28" />
      <span>
        <strong>点击选择或拖拽文档到这里</strong>
        <small>支持 PDF、DOCX、Markdown、HTML，单文件最大 50 MB</small>
      </span>
    </button>

    <p v-if="errorText" class="inline-error">{{ errorText }}</p>
    <p v-if="successText" class="inline-success">{{ successText }}</p>

    <div class="document-summary">
      <span>共 {{ total }} 个文档</span>
      <span v-if="hasProcessingDocument" class="document-processing-hint">
        <LoaderCircle :size="14" />
        正在同步入库状态
      </span>
    </div>

    <div class="document-list">
      <article v-for="document in documents" :key="document.id" class="document-card">
        <div class="document-file-icon" :class="document.status">
          <FileText :size="21" />
        </div>

        <div class="document-info">
          <div class="document-title-row">
            <strong :title="document.name">{{ document.name }}</strong>
            <span class="document-status" :class="document.status">
              <CheckCircle2 v-if="document.status === 'ready'" :size="14" />
              <AlertCircle v-else-if="document.status === 'failed'" :size="14" />
              <LoaderCircle v-else :size="14" />
              {{ statusLabel(document.status) }}
            </span>
          </div>
          <div class="document-meta">
            <span>{{ formatSize(document.size) }}</span>
            <span>版本 {{ document.version }}</span>
            <span><Clock3 :size="13" />{{ formatDate(document.updated_at) }}</span>
          </div>
          <small v-if="document.error_message" class="document-error">
            {{ document.error_message }}
          </small>
        </div>

        <div class="document-actions">
          <button
            v-if="document.status === 'failed'"
            class="icon-button"
            type="button"
            title="重新处理"
            :disabled="activeDocumentId === document.id"
            @click="retry(document)"
          >
            <RotateCcw :size="17" />
          </button>
          <button
            class="icon-button danger"
            type="button"
            title="删除文档"
            :disabled="!canDelete(document) || activeDocumentId === document.id"
            @click="removeDocument(document)"
          >
            <Trash2 :size="17" />
          </button>
        </div>
      </article>

      <p v-if="isLoading && !documents.length" class="empty-state">加载文档中</p>
      <p v-else-if="!documents.length" class="empty-state">暂无文档，上传后将自动写入 RAG 向量库</p>
    </div>

    <footer v-if="total > pageSize" class="document-pagination">
      <button
        class="secondary-button"
        type="button"
        :disabled="page <= 1 || isLoading"
        @click="goToPage(page - 1)"
      >
        上一页
      </button>
      <span>第 {{ page }} / {{ pageCount }} 页</span>
      <button
        class="secondary-button"
        type="button"
        :disabled="page >= pageCount || isLoading"
        @click="goToPage(page + 1)"
      >
        下一页
      </button>
    </footer>
  </section>
</template>

<style scoped>
.document-manager {
  grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
}

.document-upload-button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: 8px;
  color: #ffffff;
  background: linear-gradient(135deg, #ff6f91, #34c5d8);
  cursor: pointer;
  font-weight: 800;
}

.document-upload-button:disabled,
.document-dropzone:disabled,
.document-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.document-dropzone {
  display: flex;
  width: 100%;
  min-height: 96px;
  align-items: center;
  justify-content: center;
  gap: 13px;
  border: 1px dashed rgba(52, 168, 191, 0.5);
  border-radius: 8px;
  color: #53627f;
  background: rgba(244, 251, 255, 0.72);
  cursor: pointer;
  text-align: left;
  transition: 160ms ease;
}

.document-dropzone:hover,
.document-dropzone.dragging {
  border-color: #34a8bf;
  background: rgba(232, 249, 252, 0.95);
  transform: translateY(-1px);
}

.document-dropzone > svg {
  flex: 0 0 auto;
  color: #34a8bf;
}

.document-dropzone span {
  display: grid;
  gap: 5px;
}

.document-dropzone strong {
  color: #243047;
}

.document-dropzone small,
.document-summary,
.document-meta {
  color: #6a7894;
  font-size: 0.78rem;
}

.document-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 24px;
  font-weight: 700;
}

.document-processing-hint,
.document-meta span,
.document-pagination {
  display: flex;
  align-items: center;
}

.document-processing-hint {
  gap: 6px;
  color: #278da2;
}

.document-processing-hint svg,
.document-status.uploading svg,
.document-status.parsing svg,
.document-status.indexing svg,
.spinning {
  animation: document-spin 0.9s linear infinite;
}

.document-list {
  display: grid;
  align-content: start;
  gap: 9px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.document-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 82px;
  padding: 13px;
  border: 1px solid rgba(126, 143, 178, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}

.document-file-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: linear-gradient(135deg, #34c5d8, #53627f);
}

.document-file-icon.ready {
  background: linear-gradient(135deg, #42b883, #278da2);
}

.document-file-icon.failed {
  background: linear-gradient(135deg, #ff8a65, #e24c63);
}

.document-info {
  display: grid;
  min-width: 0;
  gap: 7px;
}

.document-title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.document-title-row > strong {
  min-width: 0;
  overflow: hidden;
  color: #1e2941;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-status {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
  padding: 4px 7px;
  border-radius: 999px;
  color: #278da2;
  background: #eefafd;
  font-size: 0.72rem;
  font-weight: 800;
}

.document-status.ready {
  color: #258d55;
  background: #eefaf3;
}

.document-status.failed {
  color: #d53d56;
  background: #fff1f3;
}

.document-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 13px;
}

.document-meta span {
  gap: 4px;
}

.document-error {
  overflow: hidden;
  color: #d53d56;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-actions {
  display: flex;
  gap: 7px;
}

.document-actions .icon-button {
  width: 36px;
  height: 36px;
}

.document-pagination {
  justify-content: center;
  gap: 12px;
  padding-top: 4px;
  color: #6a7894;
  font-size: 0.8rem;
}

@keyframes document-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 620px) {
  .document-dropzone {
    padding: 16px;
  }

  .document-card {
    grid-template-columns: 38px minmax(0, 1fr);
  }

  .document-actions {
    grid-column: 2;
  }

  .document-title-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }
}
</style>
