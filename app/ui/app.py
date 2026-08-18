import os
import requests
import streamlit as st
import time

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Future Process Designer | Retail Operations",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38BDF8;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #CBD5E1;
        margin-bottom: 1.5rem;
    }
    .status-completed {
        background-color: #ECFDF5;
        border: 1px solid #10B981;
        color: #065F46;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .status-pending {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        color: #92400E;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-human {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-ai-assisted {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-automated {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-hitl {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .prov-evidence {
        background-color: #F0FDF4;
        border-left: 4px solid #10B981;
        padding: 10px 14px;
        border-radius: 6px;
        margin-top: 8px;
        font-size: 0.88rem;
    }
    .prov-analytic {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 10px 14px;
        border-radius: 6px;
        margin-top: 8px;
        font-size: 0.88rem;
    }
    .evidence-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 6px;
        font-size: 0.85rem;
    }
    .empty-state-box {
        background-color: #F8FAFC;
        border: 2px dashed #CBD5E1;
        border-radius: 8px;
        padding: 30px;
        text-align: center;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

def fetch_processes():
    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/processes", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Cannot connect to backend service at {BACKEND_URL}: {e}")
    return []

def fetch_process_detail(proc_id):
    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/processes/{proc_id}", timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Error fetching process details: {e}")
    return None

def run_transformation(proc_id):
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    stages = [
        "Stage 1/5: Analyzing operational bottlenecks & formulating research queries...",
        "Stage 2/5: Executing live web research & indexing embeddings into pgvector...",
        "Stage 3/5: Mapping research evidence to activities & evaluating AI opportunities...",
        "Stage 4/5: Re-architecting future process & assigning responsibility matrix...",
        "Stage 5/5: Validating qualitative impact metrics & persisting to PostgreSQL..."
    ]
    
    for idx, stage_msg in enumerate(stages):
        status_placeholder.info(f"⏳ **Transforming...** {stage_msg}")
        progress_bar.progress(int((idx + 1) * 20))
        time.sleep(0.3)
        
    try:
        res = requests.post(f"{BACKEND_URL}/api/v1/processes/{proc_id}/transform", timeout=60)
        progress_bar.progress(100)
        if res.status_code == 200:
            status_placeholder.success("✅ **Transformation Complete!** Results persisted to PostgreSQL database.")
            time.sleep(0.5)
            status_placeholder.empty()
            progress_bar.empty()
            return res.json()
        else:
            status_placeholder.error(f"Transformation failed: {res.text}")
    except Exception as e:
        status_placeholder.error(f"Error triggering transformation: {e}")
        
    progress_bar.empty()
    return None

def fetch_health():
    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/health", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

# --- SIDEBAR & NAVIGATION ---
st.sidebar.title("⚡ Process Designer")
st.sidebar.caption("Retail Operations AI Transformation Engine")

health_info = fetch_health()
if health_info.get("langsmith_tracing_enabled"):
    st.sidebar.success(f"🟢 **LangSmith Tracing Active**\nProject: `{health_info.get('langsmith_project', 'default')}`")
else:
    st.sidebar.caption("⚪ **LangSmith Tracing Inactive** (Set `LANGCHAIN_TRACING_V2=true` & `LANGCHAIN_API_KEY` in `.env`)")

processes = fetch_processes()
proc_options = {p["name"]: p["id"] for p in processes}

selected_proc_name = st.sidebar.selectbox(
    "Select Retail Process",
    options=list(proc_options.keys()) if proc_options else ["Inventory Management / Replenishment"]
)

st.sidebar.divider()
st.sidebar.subheader("Dynamic Evaluation")
if st.sidebar.button("➕ Create Custom Process", use_container_width=True):
    st.session_state["show_custom_form"] = True

# --- MAIN CONTENT LAYOUT ---
st.markdown('<div class="main-header">AI Future Process Designer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Enterprise Retail Process Optimization — Explore where AI can be integrated into enterprise retail processes to improve efficiency, reduce operational bottlenecks, and enable smarter workflows</div>', unsafe_allow_html=True)

# Custom Process Creation Form
if st.session_state.get("show_custom_form", False):
    st.subheader("Define a New Retail Process")
    st.info("Dynamic Evaluation: Enter your process description and bottlenecks below. The AI pipeline will automatically derive structured activities, roles, systems, and AI opportunities for PostgreSQL storage.")
    
    with st.form("custom_proc_form"):
        c_name = st.text_input("Process Name", placeholder="e.g., Seasonal Inventory Clearance & Markdowns")
        c_ind = st.text_input("Industry / Business Context", placeholder="e.g., Retail / E-commerce")
        c_desc = st.text_area("Process Overview", placeholder="Brief high-level summary of the business process...")
        c_proc_text = st.text_area(
            "Current Process / Activities",
            placeholder="Enter a simple list or description of current steps:\n- Step 1: Weekly stock audit and inventory check\n- Step 2: Manual tag printing and shelf replacement"
        )
        c_prob_text = st.text_area(
            "Key Problems / Bottlenecks",
            placeholder="Describe operational pain points, manual delays, or errors:\n- Sales data lags by 3 days causing stockouts\n- Manual tagging leads to high pricing mismatch errors"
        )
        
        col_cancel, col_submit = st.columns([1, 4])
        with col_submit:
            submitted = st.form_submit_button("Save Process & Derive Model", type="primary", use_container_width=True)
        with col_cancel:
            if st.form_submit_button("Cancel", use_container_width=True):
                st.session_state["show_custom_form"] = False
                st.rerun()

        if submitted:
            if not c_name or not c_desc or not c_proc_text:
                st.error("Please provide a Process Name, Process Overview, and Current Process description.")
            else:
                payload = {
                    "name": c_name,
                    "industry": c_ind if c_ind else "Retail / E-commerce",
                    "description": c_desc,
                    "current_process_text": c_proc_text,
                    "problems_text": c_prob_text
                }
                res = requests.post(f"{BACKEND_URL}/api/v1/processes", json=payload)
                if res.status_code == 201:
                    st.success("New process analyzed and structured components saved to PostgreSQL!")
                    st.session_state["show_custom_form"] = False
                    st.rerun()
                else:
                    st.error(f"Failed to save custom process: {res.text}")

elif selected_proc_name and proc_options:
    selected_id = proc_options[selected_proc_name]
    proc_detail = fetch_process_detail(selected_id)
    
    if proc_detail:
        st.subheader(f"📌 {proc_detail['name']}")
        st.caption(f"**Industry:** {proc_detail['industry']} | **Type:** {'Custom Runtime Process' if proc_detail['is_custom'] else 'Preloaded Retail Baseline'}")
        st.info(proc_detail['description'])

        future_proc = proc_detail.get("future_process")
        has_transformed = bool(future_proc and future_proc.get("future_activities"))

        # Header Status Dashboard
        m1, m2, m3 = st.columns([1.5, 2, 2.5])
        with m1:
            st.metric("Current Activities", len(proc_detail['current_activities']))
        with m2:
            if has_transformed:
                st.markdown('<div class="status-completed">🟢 Transformation Completed</div>', unsafe_allow_html=True)
                if future_proc.get("created_at"):
                    st.caption(f"Executed: {future_proc['created_at'][:16].replace('T', ' ')} UTC")
            else:
                st.markdown('<div class="status-pending">🔴 Not Transformed Yet</div>', unsafe_allow_html=True)
                st.caption("Awaiting 5-Stage LangGraph Run")
        with m3:
            col_tf, col_del = st.columns([3, 1])
            with col_tf:
                if st.button("🚀 Transform Process with AI", type="primary", use_container_width=True):
                    run_transformation(selected_id)
                    st.rerun()
            with col_del:
                if st.button("🗑️ Delete", use_container_width=True, help="Delete this process and all its data from PostgreSQL"):
                    res_del = requests.delete(f"{BACKEND_URL}/api/v1/processes/{selected_id}")
                    if res_del.status_code == 200:
                        st.success("Process deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete process.")

        st.divider()

        # Tabs Layout
        tab_current, tab_future, tab_evidence, tab_impact = st.tabs([
            "📋 Current State Process",
            "✨ Future State Process & Provenance",
            "🔍 Live External Research Evidence",
            "📊 Impact & Assumptions"
        ])

        # TAB 1: CURRENT STATE PROCESS
        with tab_current:
            st.markdown("### Current Operational Baseline (PostgreSQL)")
            st.caption("Extracted directly from structured process activities in PostgreSQL.")
            
            for act in proc_detail['current_activities']:
                with st.expander(f"Activity #{act['sequence_order']}: {act['name']}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Role:** `{act['role']}`")
                    c2.markdown(f"**System:** `{act['system']}`")
                    c3.markdown(f"**Sequence Order:** #{act['sequence_order']}")
                    if act.get('operational_problem'):
                        st.warning(f"⚠️ **Operational Problem:** {act['operational_problem']}")

        # TAB 2: FUTURE STATE PROCESS & PROVENANCE
        with tab_future:
            st.markdown("### Future-State Process & Provenance Mapping")
            if not has_transformed:
                st.markdown("""
                <div class="empty-state-box">
                    <h3>⚠️ Transformation Has Not Been Executed Yet</h3>
                    <p style="color: #64748B;">This process currently exists only as a baseline current-state model.<br/>
                    Click <b>'🚀 Transform Process with AI'</b> to run the 5-stage LangGraph workflow, perform live web research, and generate the evidence-backed future state.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption(f"Loaded from PostgreSQL (Future Process ID: `{future_proc['id'][:8]}...`)")
                for fact in future_proc['future_activities']:
                    exec_type = fact['execution_type']
                    if exec_type == "human":
                        badge_html = '<span class="badge-human">🔴 Human Only</span>'
                    elif exec_type == "AI-assisted":
                        badge_html = '<span class="badge-ai-assisted">🟡 AI-Assisted</span>'
                    elif exec_type == "automated":
                        badge_html = '<span class="badge-automated">🟢 Fully Automated</span>'
                    else:
                        badge_html = '<span class="badge-hitl">🔵 Human-in-the-Loop</span>'

                    with st.container():
                        st.markdown(f"#### Step {fact['sequence_order']}: {fact['name']} &nbsp; {badge_html}", unsafe_allow_html=True)
                        st.markdown(f"**Primary System:** `{fact['primary_system']}` | **Human Role:** `{fact.get('human_involvement_role') or 'None (Fully Automated)'}`")
                        st.markdown(f"**Design Rationale:** {fact['rationale']}")
                        
                        # Provenance Labeling (Strict Rule Implementation)
                        prov = fact.get("provenance_status", "ANALYTIC_RECOMMENDATION")
                        linked_ev = fact.get("linked_evidence")
                        
                        if prov == "EVIDENCE_BACKED":
                            ev_details = ""
                            if linked_ev:
                                ev_details = (
                                    f'<div class="evidence-box">'
                                    f'<b>Linked Evidence:</b> <a href="{linked_ev["source_url"]}" target="_blank">{linked_ev["title"]}</a><br/>'
                                    f'<i>"{linked_ev["snippet"][:180]}..."</i><br/>'
                                    f'<small style="color: #64748B;">Retrieved At: {linked_ev.get("retrieved_at", "N/A")[:16].replace("T", " ")}</small>'
                                    f'</div>'
                                )
                            st.markdown(
                                f'<div class="prov-evidence">✅ <b>Research-Supported Recommendation</b><br/>'
                                f'This AI intervention is grounded in live external web research evidence.<br/>'
                                f'{ev_details}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="prov-analytic">💡 <b>AI Analytical Suggestion (Unbacked by External Evidence)</b><br/>'
                                f'This recommendation is derived purely from AI analytical synthesis and process optimization heuristics. It has NOT been verified by external empirical web research.</div>',
                                unsafe_allow_html=True
                            )
                        st.divider()

        # TAB 3: LIVE EXTERNAL RESEARCH EVIDENCE
        with tab_evidence:
            st.markdown("### Live External Web Research Evidence")
            evidence_items = proc_detail.get("evidence_items", [])
            
            if not has_transformed or not evidence_items:
                st.markdown("""
                <div class="empty-state-box">
                    <h3>🔍 No Live Research Evidence Recorded</h3>
                    <p style="color: #64748B;">No external research evidence has been retrieved for this specific process.<br/>
                    Click <b>'🚀 Transform Process with AI'</b> to launch dynamic web search (DuckDuckGo/Tavily) and store evidence linked strictly to this process.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption(f"Displaying {len(evidence_items)} live web research records stored in PostgreSQL `research_evidence` table for this process.")
                for ev in evidence_items:
                    with st.container():
                        st.markdown(f"##### 📄 [{ev['title']}]({ev['source_url']})")
                        st.caption(f"**Target Activity ID:** `{ev.get('activity_id') or 'General Process'}` | **Query:** `{ev['search_query']}` | **Retrieved:** {ev.get('retrieved_at', 'N/A')[:16].replace('T', ' ')} UTC")
                        st.markdown(f"> _{ev['snippet']}_")
                        st.divider()

        # TAB 4: IMPACT & ASSUMPTIONS
        with tab_impact:
            st.markdown("### Qualitative Business Impact & Operational Risk Assessment")
            if not has_transformed or not future_proc.get("impact_assessment"):
                st.markdown("""
                <div class="empty-state-box">
                    <h3>📊 Impact & Assumptions Not Generated Yet</h3>
                    <p style="color: #64748B;">Impact assessment metrics will be computed and persisted after running Stage 5 of the LangGraph workflow.<br/>
                    Click <b>'🚀 Transform Process with AI'</b> to execute transformation.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                imp = future_proc["impact_assessment"]
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Overall Impact Level", imp["impact_level"])
                k2.metric("Implementation Complexity", imp["implementation_complexity"])
                k3.metric("Evidence Confidence Level", imp["confidence_level"])
                
                st.divider()
                
                c_ass, c_ben = st.columns(2)
                with c_ass:
                    st.markdown("#### 📝 Explicit Process Assumptions")
                    for ass in imp.get("explicit_assumptions", []):
                        st.markdown(f"- {ass}")
                with c_ben:
                    st.markdown("#### 🎯 Qualitative Business Benefits")
                    for ben in imp.get("qualitative_benefits", []):
                        st.markdown(f"- ✅ {ben}")
                        
                st.divider()
                st.markdown("#### ⚠️ Operational Risks & Mitigation Strategies")
                for r in imp.get("operational_risks", []):
                    st.error(f"**Risk:** {r.get('risk')}  \n**Mitigation:** {r.get('mitigation')}")
                    
                if imp.get("calculated_roi_notes"):
                    st.info(f"**Quantitative ROI Notes:** {imp['calculated_roi_notes']}")
