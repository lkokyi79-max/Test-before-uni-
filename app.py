import streamlit as st
import json
import plotly.graph_objects as go
from collections import defaultdict
import time
import os

# ---------- 页面设置 ----------
st.set_page_config(
    page_title="大学前兴趣测试", 
    layout="wide",  # 改为宽屏布局以容纳更多内容
    initial_sidebar_state="expanded",
    menu_items=None
)

# ---------- 初始化会话状态 ----------
if "page" not in st.session_state:
    st.session_state.page = 0  # 当前页码 (0: 1-100题, 1: 101-200题)
if "answers" not in st.session_state:
    st.session_state.answers = {}  # 存储答案 {问题索引: 选项索引}
if "skipped" not in st.session_state:
    st.session_state.skipped = set()  # 跳过的题目索引
if "test_completed" not in st.session_state:
    st.session_state.test_completed = False
if "auto_save" not in st.session_state:
    st.session_state.auto_save = True
if "show_compact" not in st.session_state:
    st.session_state.show_compact = True  # 紧凑模式

# ---------- 加载问题 ----------
@st.cache_data(ttl=3600)  # 缓存1小时
def load_questions():
    with open("questions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]

questions = load_questions()
total_questions = len(questions)
questions_per_page = 100  # 每页100题
total_pages = (total_questions + questions_per_page - 1) // questions_per_page  # 应该是2页

# ---------- 侧边栏：进度管理和设置 ----------
with st.sidebar:
    st.header("📊 测试进度")
    
    # 统计信息
    answered_count = len(st.session_state.answers)
    skipped_count = len(st.session_state.skipped)
    remaining = total_questions - answered_count - skipped_count
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("已完成", answered_count)
    with col2:
        st.metric("已跳过", skipped_count)
    with col3:
        st.metric("待回答", remaining)
    
    # 总体进度条
    progress = (answered_count + skipped_count) / total_questions
    st.progress(progress, text=f"总体进度: {progress*100:.1f}%")
    
    st.divider()
    
    st.header("⚙️ 显示设置")
    
    # 紧凑模式切换
    st.session_state.show_compact = st.toggle("紧凑模式", value=st.session_state.show_compact)
    
    # 自动保存选项
    st.session_state.auto_save = st.toggle("自动保存", value=st.session_state.auto_save)
    
    st.divider()
    
    st.header("📁 进度管理")
    
    # 手动保存
    if st.button("💾 手动保存进度", use_container_width=True):
        save_data = {
            "answers": st.session_state.answers,
            "skipped": list(st.session_state.skipped),
            "page": st.session_state.page
        }
        st.session_state.save_data = json.dumps(save_data, ensure_ascii=False)
        st.download_button(
            label="📥 点击下载进度文件",
            data=st.session_state.save_data,
            file_name="interest_test_progress.json",
            mime="application/json",
            use_container_width=True
        )
    
    # 加载进度
    uploaded_file = st.file_uploader("📂 加载进度文件", type=['json'])
    if uploaded_file is not None:
        try:
            load_data = json.load(uploaded_file)
            st.session_state.answers = load_data.get("answers", {})
            st.session_state.skipped = set(load_data.get("skipped", []))
            st.session_state.page = load_data.get("page", 0)
            st.success("✅ 进度加载成功！")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"❌ 文件格式错误: {e}")
    
    st.divider()
    
    # 快速导航
    st.header("🔍 快速导航")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 第1页 (1-100题)", use_container_width=True, 
                    disabled=st.session_state.page==0):
            st.session_state.page = 0
            st.rerun()
    with col2:
        if st.button("📄 第2页 (101-200题)", use_container_width=True,
                    disabled=st.session_state.page==1):
            st.session_state.page = 1
            st.rerun()

# ---------- 主页面 ----------
st.title("🎓 大学前兴趣测试 (200题)")

if not st.session_state.test_completed:
    # 计算当前页的题目范围
    start_idx = st.session_state.page * questions_per_page
    end_idx = min(start_idx + questions_per_page, total_questions)
    
    # 页面标题
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"📄 第 {st.session_state.page + 1} 页 / 共 {total_pages} 页")
        st.caption(f"显示第 {start_idx + 1} - {end_idx} 题")
    
    with col2:
        # 本页进度
        page_answered = sum(1 for i in range(start_idx, end_idx) if str(i) in st.session_state.answers)
        page_skipped = sum(1 for i in range(start_idx, end_idx) if i in st.session_state.skipped)
        page_total = end_idx - start_idx
        page_progress = (page_answered + page_skipped) / page_total
        st.metric("本页进度", f"{page_progress*100:.1f}%")
    
    with col3:
        if st.button("📊 提交并查看结果", type="primary", use_container_width=True):
            if answered_count + skipped_count == total_questions:
                st.session_state.test_completed = True
                st.rerun()
            else:
                st.warning(f"还有 {remaining} 题未完成")
    
    st.divider()
    
    # 根据模式显示题目
    if st.session_state.show_compact:
        # ---------- 紧凑模式：表格形式 ----------
        st.info("💡 紧凑模式：每行显示5题，点击选项快速选择")
        
        # 创建表格布局
        rows = (page_total + 4) // 5  # 每行5题
        
        for row in range(rows):
            cols = st.columns(5)
            for col_idx in range(5):
                question_idx = start_idx + row * 5 + col_idx
                if question_idx >= end_idx:
                    break
                
                with cols[col_idx]:
                    q = questions[question_idx]
                    question_num = question_idx + 1
                    
                    # 题目卡片
                    with st.container():
                        # 题目头部
                        if question_idx in st.session_state.skipped:
                            st.markdown(f"**{question_num}.** ⏭️ 已跳过")
                        else:
                            st.markdown(f"**{question_num}.** {q['text'][:20]}...")
                        
                        # 选项（用字母表示）
                        options = q["options"]
                        opt_letters = ['A', 'B', 'C', 'D']
                        
                        # 获取已保存的答案
                        saved_answer = st.session_state.answers.get(str(question_idx))
                        saved_letter = None
                        if saved_answer:
                            for i, opt in enumerate(options):
                                if opt["text"] == saved_answer:
                                    saved_letter = opt_letters[i]
                                    break
                        
                        # 显示选项按钮
                        for i, opt in enumerate(options):
                            letter = opt_letters[i]
                            field = opt["field"]
                            
                            # 根据领域设置颜色
                            color_map = {
                                "科学": "🔵", "人文": "🟠", "艺术": "🟢", 
                                "商业": "🔴", "服务": "🟣"
                            }
                            
                            # 按钮文字
                            if saved_letter == letter:
                                btn_text = f"✅ {letter}"
                            else:
                                btn_text = f"{color_map[field]} {letter}"
                            
                            # 按钮
                            if st.button(
                                btn_text,
                                key=f"q_{question_idx}_{i}",
                                use_container_width=True,
                                type="primary" if saved_letter == letter else "secondary",
                                disabled=question_idx in st.session_state.skipped
                            ):
                                if question_idx not in st.session_state.skipped:
                                    st.session_state.answers[str(question_idx)] = opt["text"]
                                    if st.session_state.auto_save:
                                        st.toast(f"✓ 第{question_num}题已保存", icon="✅")
                                    st.rerun()
                        
                        # 跳过按钮
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if question_idx in st.session_state.skipped:
                                if st.button("✅ 取消", key=f"unskip_{question_idx}", use_container_width=True):
                                    st.session_state.skipped.remove(question_idx)
                                    st.rerun()
                            else:
                                if st.button("⏭️ 跳过", key=f"skip_{question_idx}", use_container_width=True):
                                    st.session_state.skipped.add(question_idx)
                                    if str(question_idx) in st.session_state.answers:
                                        del st.session_state.answers[str(question_idx)]
                                    st.toast(f"⏭️ 第{question_num}题已跳过")
                                    st.rerun()
                        
                        with col_b:
                            # 显示当前选择
                            if saved_letter:
                                st.caption(f"已选: {saved_letter}")
                            elif question_idx in st.session_state.skipped:
                                st.caption("已跳过")
                            else:
                                st.caption("未选")
                    
                    st.divider()
    
    else:
        # ---------- 详细模式：完整显示题目 ----------
        st.info("📝 详细模式：每题完整显示，适合仔细思考")
        
        for idx in range(start_idx, end_idx):
            q = questions[idx]
            question_num = idx + 1
            
            # 判断是否已跳过
            is_skipped = idx in st.session_state.skipped
            
            # 构建选项列表
            option_texts = [opt["text"] for opt in q["options"]]
            
            # 获取已保存的答案
            saved_answer = st.session_state.answers.get(str(idx))
            
            col1, col2 = st.columns([5, 1])
            with col1:
                if is_skipped:
                    st.markdown(f"**问题 {question_num}** (已跳过) ⏭️")
                else:
                    st.markdown(f"**问题 {question_num}**")
                st.write(q["text"])
            
            with col2:
                # 跳过/取消跳过按钮
                if is_skipped:
                    if st.button("✅ 取消跳过", key=f"unskip_{idx}"):
                        st.session_state.skipped.remove(idx)
                        st.rerun()
                else:
                    if st.button("⏭️ 跳过", key=f"skip_{idx}"):
                        st.session_state.skipped.add(idx)
                        if str(idx) in st.session_state.answers:
                            del st.session_state.answers[str(idx)]
                        st.rerun()
            
            # 如果不是跳过的题目，显示选项
            if not is_skipped:
                # 确定默认选中的索引
                default_index = None
                if saved_answer is not None:
                    try:
                        default_index = option_texts.index(saved_answer)
                    except:
                        default_index = None
                
                selected = st.radio(
                    label="请选择一个选项",
                    options=option_texts,
                    key=f"q_{idx}",
                    index=default_index,
                    label_visibility="collapsed",
                    horizontal=True  # 水平排列选项
                )
                
                # 如果用户选了，更新答案
                if selected:
                    st.session_state.answers[str(idx)] = selected
                    if st.session_state.auto_save:
                        st.caption("✓ 已自动保存")
                elif not saved_answer:
                    st.warning("请选择一个选项或点击跳过")
            
            st.divider()
    
    # 页脚导航
    st.divider()
    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
    
    with col1:
        if st.session_state.page > 0:
            if st.button("◀ 上一页 (1-100题)", use_container_width=True):
                st.session_state.page -= 1
                st.rerun()
    
    with col2:
        if st.session_state.page < total_pages - 1:
            if st.button("下一页 (101-200题) ▶", use_container_width=True):
                st.session_state.page += 1
                st.rerun()
    
    with col4:
        # 提交按钮
        if answered_count + skipped_count == total_questions:
            if st.button("📊 查看完整报告", type="primary", use_container_width=True):
                st.session_state.test_completed = True
                st.rerun()

# ---------- 结果页面 (保持不变) ----------
else:
    st.subheader("📊 你的兴趣测试结果")
    
    # 统计各领域得分
    scores = defaultdict(int)
    field_count = defaultdict(int)
    
    for idx_str, answer_text in st.session_state.answers.items():
        idx = int(idx_str)
        options = questions[idx]["options"]
        for opt in options:
            if opt["text"] == answer_text:
                field = opt["field"]
                scores[field] += 1
                field_count[field] += 1
                break
    
    all_fields = ["科学", "人文", "艺术", "商业", "服务"]
    for field in all_fields:
        if field not in scores:
            scores[field] = 0
        if field not in field_count:
            field_count[field] = 0
    
    # 计算得分率
    score_percentages = {}
    for field in all_fields:
        max_possible = 160
        actual_max = field_count[field]
        if actual_max > 0:
            score_percentages[field] = (scores[field] / actual_max) * 100
        else:
            score_percentages[field] = 0
    
    # 显示图表
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = go.Figure(data=[
            go.Bar(
                x=list(scores.keys()),
                y=list(scores.values()),
                marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                text=list(scores.values()),
                textposition='auto'
            )
        ])
        fig1.update_layout(
            title="绝对得分",
            xaxis_title="领域",
            yaxis_title="得分",
            yaxis=dict(range=[0, 160])
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = go.Figure(data=[
            go.Bar(
                x=list(score_percentages.keys()),
                y=list(score_percentages.values()),
                marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                text=[f"{v:.1f}%" for v in score_percentages.values()],
                textposition='auto'
            )
        ])
        fig2.update_layout(
            title="得分率 (已答题百分比)",
            xaxis_title="领域",
            yaxis_title="得分率 (%)",
            yaxis=dict(range=[0, 100])
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # 结果解读
    st.divider()
    st.subheader("🔍 结果分析")
    
    max_percentage = max(score_percentages.values())
    top_fields = [field for field, pct in score_percentages.items() if pct == max_percentage]
    
    st.success("### 最强兴趣领域")
    if len(top_fields) == 1:
        st.success(f"**{top_fields[0]}**")
        
        suggestions = {
            "科学": "🔬 适合专业：计算机、物理、化学、生物、工程、数学、人工智能",
            "人文": "📚 适合专业：文学、历史、哲学、社会学、语言学、人类学、考古学",
            "艺术": "🎨 适合专业：美术、音乐、设计、戏剧、影视、艺术史、数字媒体",
            "商业": "💼 适合专业：经济学、金融学、管理学、市场营销、国际贸易、会计",
            "服务": "❤️ 适合专业：医学、护理、教育、心理学、社会工作、体育、公共卫生"
        }
        st.write(suggestions[top_fields[0]])
    else:
        st.success(f"**{', '.join(top_fields)}**")
        st.write("你的兴趣比较广泛，可以考虑交叉学科专业，如：")
        st.write("- 科学+艺术：数字媒体、建筑学、工业设计")
        st.write("- 人文+商业：文化产业管理、市场营销")
        st.write("- 科学+服务：医学、生物工程")
    
    # 详细得分
    st.divider()
    st.subheader("📋 详细得分")
    
    data = []
    for field in all_fields:
        data.append({
            "领域": field,
            "得分": scores[field],
            "已答题数": field_count[field],
            "得分率": f"{score_percentages[field]:.1f}%"
        })
    
    st.table(data)
    
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 重新测试", use_container_width=True):
            for key in ["answers", "skipped", "page", "test_completed"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col2:
        if st.button("✏️ 返回修改答案", use_container_width=True):
            st.session_state.test_completed = False
            st.rerun()
    
    with col3:
        # 保存结果
        result_data = {
            "得分": dict(scores),
            "得分率": score_percentages,
            "最强领域": top_fields
        }
        st.download_button(
            label="📥 下载结果",
            data=json.dumps(result_data, ensure_ascii=False, indent=2),
            file_name="interest_test_result.json",
            mime="application/json",
            use_container_width=True
        )
