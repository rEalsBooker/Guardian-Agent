"""
Guardian-Agent V2: 基于 RAG 与分布式缓存的自愈自动化系统
GitHub Repository Ready Version
"""
import streamlit as st
import time
import json
import os
import datetime
import redis
import pandas as pd
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. 全局配置 (建议生产环境使用环境变量)
# ==========================================
API_KEY = "YOUR KEY"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "deepseek-ai/DeepSeek-V3"

# 初始化项目目录结构
for folder in ["./logs", "./screenshots", "./vector_db"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

st.set_page_config(
    page_title="Guardian-Agent | AI 自愈自动化平台",
    layout="wide",
    page_icon="🛡️"
)


# ==========================================
# 2. 自动化代理引擎 (核心逻辑)
# ==========================================
class AutomationEngine:
    def __init__(self, log_widget, thought_widget):
        self.log_p = log_widget
        self.thought_p = thought_widget

        # 初始化 AI 组件
        self.llm = ChatOpenAI(api_key=API_KEY, base_url=BASE_URL, model=MODEL)
        self.embeddings = OpenAIEmbeddings(api_key=API_KEY, base_url=BASE_URL, model="BAAI/bge-m3")
        self.vector_store = Chroma(
            collection_name="recovery_kb",
            embedding_function=self.embeddings,
            persist_directory="./vector_db"
        )

        # Redis 状态管理
        try:
            self.redis = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
            self.redis.ping()
            self.has_redis = True
        except Exception:
            self.has_redis = False

        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.driver = None

    def _log(self, msg, level="info"):
        """向 UI 界面输出审计日志"""
        icons = {"info": "🔹", "success": "✅", "warn": "⚠️", "error": "❌"}
        self.log_p.write(f"{icons.get(level, '🔹')} {msg}")

    def _think(self, title, content):
        """向 UI 界面展示 AI 推理链"""
        with self.thought_p:
            st.caption(f"🧠 {title}")
            if isinstance(content, dict):
                st.json(content)
            else:
                st.code(content, language="text")

    def _self_heal(self, selector, error):
        """核心自愈逻辑：结合 RAG 经验与 DOM 分析"""
        self._log(f"检测到异常，正在尝试 AI 自愈...", "warn")

        # 1. 检索 RAG 知识库
        try:
            docs = self.vector_store.similarity_search(selector, k=1)
            experience = docs[0].page_content if docs else "暂无匹配的历史修复经验"
        except Exception:
            experience = "向量库检索失败"

        self._think("RAG 检索上下文", {"matched_experience": experience})

        # 2. 构建思维链 Prompt
        prompt = ChatPromptTemplate.from_template("""
        角色：自动化测试专家
        失败的选择器：{selector}
        错误类型：{err}
        参考经验：{ctx}
        当前 DOM 结构 (部分)：{dom}
        任务：请基于以上信息提供一个修正后的 CSS 选择器。
        返回格式：严格 JSON，如 {{"fixed_selector": "..."}}
        """)

        try:
            chain = prompt | self.llm
            resp = chain.invoke({
                "selector": selector,
                "err": str(error),
                "ctx": experience,
                "dom": self.driver.page_source[:1200]
            })
            # 清洗并解析 JSON
            content = resp.content.replace("```json", "").replace("```", "").strip()
            fixed = json.loads(content)
            self._think("DeepSeek 决策方案", fixed)
            return fixed.get("fixed_selector")
        except Exception as e:
            self._log(f"AI 决策链路中断: {str(e)}", "error")
            return None

    def safe_click(self, selector, timeout=5):
        """带自愈功能的安全点击方法"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            self._log(f"操作成功: {selector}", "success")
            return True
        except Exception as e:
            # 捕获异常并触发自愈，不再直接抛出红框报错
            fixed_selector = self._self_heal(selector, e)
            if fixed_selector:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, fixed_selector).click()
                    self._log(f"自愈成功：已切换至新选择器 [{fixed_selector}]", "success")
                    return True
                except Exception:
                    self._log("自愈重试失败，请检查 RAG 知识准确性", "error")
            else:
                self._log(f"无法定位元素且自愈失败: {selector}", "error")
            return False

    def run(self):
        """执行端到端业务流"""
        self._log("启动浏览器环境...", "info")
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.driver.maximize_window()

        try:
            self.driver.get("https://www.saucedemo.com/")

            # 执行标准登录流程
            self.driver.find_element(By.ID, "user-name").send_keys("standard_user")
            self.driver.find_element(By.ID, "password").send_keys("secret_sauce")
            self.driver.find_element(By.ID, "login-button").click()

            # 触发模拟故障点
            self.safe_click("#add-to-cart-wrong-id")

            # 状态持久化
            if self.has_redis:
                status = {"run_id": self.session_id, "result": "Finished", "time": str(datetime.datetime.now())}
                self.redis.set(f"task:{self.session_id}", json.dumps(status))
                self._log("任务元数据已存入 Redis", "success")

        except Exception as e:
            self._log(f"流程异常中断: {str(e)}", "error")
        finally:
            time.sleep(3)
            if self.driver:
                self.driver.quit()
            self._log("工作流结束，资源已回收", "info")


# ==========================================
# 3. Streamlit 前端交互界面
# ==========================================
st.title("🛡️ Guardian-Agent: AI-Powered Self-Healing Automation")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.header("⚙️ Infrastructure")
    # 状态检测
    try:
        r_c = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r_c.ping()
        st.success("Redis Online")
    except:
        st.error("Redis Offline")

    st.info(f"Model: {MODEL}")
    st.divider()

    # 知识库管理
    st.subheader("📁 RAG Knowledge base")
    new_exp = st.text_area("添加修复经验:", placeholder="例如：如果 ID A 失效，尝试使用选择器 B...")
    if st.button("同步至向量库", use_container_width=True):
        emb_fn = OpenAIEmbeddings(api_key=API_KEY, base_url=BASE_URL, model="BAAI/bge-m3")
        vector_db = Chroma(collection_name="recovery_kb", embedding_function=emb_fn, persist_directory="./vector_db")
        vector_db.add_texts([new_exp])
        st.toast("Knowledge Synced!", icon="✅")

# 主界面布局
tab_run, tab_history = st.tabs(["🚀 Mission Control", "📜 Audit Logs"])

with tab_run:
    col_l, col_r = st.columns([1, 1])

    with col_r:
        st.subheader("🧠 Reasoning Chain")
        thought_area = st.container(height=500, border=True)

    with col_l:
        st.subheader("🖥️ Runtime Logs")
        log_area = st.container(height=500, border=True)
        if st.button("▶️ Start Simulation Task", use_container_width=True):
            engine = AutomationEngine(log_area, thought_area)
            engine.run()

with tab_history:
    st.subheader("Historical Execution Records (Redis)")
    if st.button("Refresh from Cache"):
        try:
            r_cli = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
            keys = r_cli.keys("task:*")
            if keys:
                records = [json.loads(r_cli.get(k)) for k in keys]
                st.dataframe(pd.DataFrame(records), use_container_width=True)
            else:
                st.info("No records found in Redis.")
        except:
            st.error("Failed to connect to Redis.")