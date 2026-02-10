# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger
Version 2.2 (Fixed Image Display & Mapping)

โดย: ภาควิชาครุศาสตร์โยธา มจพ.
"""

import streamlit as st
import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from copy import deepcopy
import io

# 1. ตั้งค่าหน้าเว็บ (คงเดิม)
st.set_page_config(
    page_title="โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide"
)

# 2. CSS สำหรับตกแต่งหน้าเว็บ (คงเดิม)
st.markdown("""
<style>
    .main-header {
        font-size: 28px;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 18px;
        color: #4A5568;
        text-align: center;
        margin-bottom: 30px;
    }
    .file-section {
        background-color: #F7FAFC;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #667eea;
    }
    .section-header {
        background-color: #C6F6D5;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 15px 0 10px 0;
        font-weight: bold;
        color: #276749;
        border-left: 4px solid #38A169;
    }
    .success-box {
        background-color: #C6F6D5;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #38A169;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        padding: 10px 30px;
        border-radius: 25px;
        border: none;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# 3. ฟังก์ชันช่วยจัดการฟอนต์และการตั้งค่าหน้ากระดาษ (คงเดิม)
def set_thai_font(run, font_name="TH Sarabun New", font_size=15):
    run.font.name = font_name
    run.font.size = Pt(font_size)
    r = run._r
    rPr = r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)

def set_page_margins(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)

# 4. ฟังก์ชันรวมเนื้อหา (แก้ไขเพื่อแก้ปัญหารูปไม่แสดงผล)
def append_document(master_doc, source_doc):
    """
    คัดลอกเนื้อหาพร้อมรูปภาพจากเอกสารต้นทางไปยังเอกสารหลัก
    ป้องกันปัญหา "The picture can't be displayed" โดยการทำ Mapping Relationships ใหม่
    """
    # จัดการเรื่องรูปภาพ: คัดลอก Relationship ของรูปภาพจากต้นทางไปยังปลายทาง
    source_rels = source_doc.part.rels
    for rel_id, rel in source_rels.items():
        if "image" in rel.reltype:
            # ตรวจสอบว่ามี relationship นี้ใน master หรือยังเพื่อป้องกัน ID ซ้ำ
            if rel.target_part not in master_doc.part.rels:
                master_doc.part.relate_to(rel.target_part, rel.reltype)

    # คัดลอก Elements จาก Body
    for element in source_doc.element.body:
        if element.tag.endswith('sectPr'):
            continue
        new_element = deepcopy(element)
        master_doc.element.body.append(new_element)

# 5. ฟังก์ชันหลักในการสร้างรายงาน (คงเดิมแต่ปรับปรุงลำดับการรวม)
def merge_documents(uploaded_files, section_titles, project_name, report_date):
    merged_doc = Document()
    section = merged_doc.sections[0]
    set_page_margins(section)
    
    # ส่วนหน้าปก
    title_para = merged_doc.add_paragraph("\n\n\n\n\n")
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    main_title = merged_doc.add_paragraph()
    main_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    main_run = main_title.add_run("รายงานการออกแบบโครงสร้างชั้นทาง")
    set_thai_font(main_run, font_size=24)
    main_run.font.bold = True
    
    if project_name:
        project_para = merged_doc.add_paragraph()
        project_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        project_run = project_para.add_run(f"\n{project_name}")
        set_thai_font(project_run, font_size=20)
        project_run.font.bold = True
    
    date_para = merged_doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(f"\n\n\n\n{report_date}")
    set_thai_font(date_run, font_size=16)
    merged_doc.add_page_break()
    
    # ส่วนสารบัญ
    toc_title = merged_doc.add_paragraph()
    toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    toc_run = toc_title.add_run("สารบัญ")
    set_thai_font(toc_run, font_size=18)
    toc_run.font.bold = True
    
    section_num = 1
    # วนลูปตามลำดับ keys ที่กำหนดไว้เพื่อให้สารบัญตรงกับเนื้อหา
    file_keys = ['truck_factor', 'esals_ac', 'esals_concrete', 'cbr_analysis', 
                 'ac_design', 'jpcp_jrcp_design', 'crcp_design', 
                 'k_value_jpcp_jrcp', 'k_value_crcp', 'cost_estimate']
    
    for key in file_keys:
        if uploaded_files.get(key) is not None:
            toc_para = merged_doc.add_paragraph()
            toc_run = toc_para.add_run(f"{section_num}. {section_titles[key]}")
            set_thai_font(toc_run, font_size=15)
            section_num += 1
    
    merged_doc.add_page_break()
    
    # ส่วนเนื้อหา: รวมไฟล์ตามลำดับที่ถูกต้อง
    section_num = 1
    for key in file_keys:
        if uploaded_files.get(key) is not None:
            file = uploaded_files[key]
            file_bytes = file.read()
            file.seek(0)
            
            # หัวข้อส่วน
            section_title_para = merged_doc.add_paragraph()
            section_run = section_title_para.add_run(f"{section_num}. {section_titles[key]}")
            set_thai_font(section_run, font_size=18)
            section_run.font.bold = True
            
            # โหลดและรวมไฟล์
            source_doc = Document(io.BytesIO(file_bytes))
            append_document(merged_doc, source_doc)
            
            merged_doc.add_page_break()
            section_num += 1
            
    return merged_doc

# 6. ฟังก์ชัน Main UI (คงเดิม)
def main():
    st.markdown('<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pavement Structure Design Report Merger v2.2</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("ชื่อโครงการ", placeholder="กรอกชื่อโครงการ")
    with col2:
        report_date = st.date_input("วันที่รายงาน", datetime.now())
        report_date_str = report_date.strftime("%d/%m/%Y")
    
    section_titles = {
        'truck_factor': 'การคำนวณ Truck Factor',
        'esals_ac': 'การคำนวณ ESALs สำหรับผิวทางลาดยาง (Flexible Pavement)',
        'esals_concrete': 'การคำนวณ ESALs สำหรับผิวทางคอนกรีต (Rigid Pavement)',
        'cbr_analysis': 'การวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์',
        'ac_design': 'การออกแบบผิวทางลาดยาง (Flexible Pavement)',
        'jpcp_jrcp_design': 'การออกแบบผิวทางคอนกรีต JPCP/JRCP',
        'crcp_design': 'การออกแบบผิวทางคอนกรีต CRCP',
        'k_value_jpcp_jrcp': 'การคำนวณ Corrected Modulus of Subgrade Reaction (k-value) สำหรับ JPCP/JRCP',
        'k_value_crcp': 'การคำนวณ Corrected Modulus of Subgrade Reaction (k-value) สำหรับ CRCP',
        'cost_estimate': 'การประมาณราคาค่าก่อสร้าง'
    }
    
    st.markdown("### 📁 อัปโหลดไฟล์รายงาน (.docx)")
    uploaded_files = {}
    
    # แบ่งกลุ่มการอัปโหลด (จัดเรียง UI ให้ใช้งานง่าย)
    st.markdown('<div class="section-header">📊 1. ข้อมูลพื้นฐานและการจราจร</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: uploaded_files['truck_factor'] = st.file_uploader("Truck Factor", type=['docx'])
    with c2: uploaded_files['esals_ac'] = st.file_uploader("ESALs (Flexible)", type=['docx'])
    with c3: uploaded_files['esals_concrete'] = st.file_uploader("ESALs (Rigid)", type=['docx'])

    st.markdown('<div class="section-header">🔬 2. การวิเคราะห์วัสดุและออกแบบ</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: uploaded_files['cbr_analysis'] = st.file_uploader("CBR Analysis", type=['docx'])
    with c2: uploaded_files['ac_design'] = st.file_uploader("Flexible Design (AC)", type=['docx'])

    st.markdown('<div class="section-header">🏗️ 3. งานผิวทางคอนกรีต</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: uploaded_files['jpcp_jrcp_design'] = st.file_uploader("JPCP/JRCP Design", type=['docx'])
    with c2: uploaded_files['crcp_design'] = st.file_uploader("CRCP Design", type=['docx'])
    
    c1, c2 = st.columns(2)
    with c1: uploaded_files['k_value_jpcp_jrcp'] = st.file_uploader("k-value (JPCP/JRCP)", type=['docx'])
    with c2: uploaded_files['k_value_crcp'] = st.file_uploader("k-value (CRCP)", type=['docx'])

    st.markdown('<div class="section-header">💰 4. งบประมาณ</div>', unsafe_allow_html=True)
    uploaded_files['cost_estimate'] = st.file_uploader("การประมาณราคา", type=['docx'])

    st.markdown("---")
    file_count = sum(1 for f in uploaded_files.values() if f is not None)
    
    if st.button("🔄 รวมไฟล์และสร้างรายงาน", use_container_width=True):
        if file_count == 0:
            st.error("❌ กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
        else:
            with st.spinner("กำลังประมวลผลรูปภาพและเนื้อหา..."):
                try:
                    merged_doc = merge_documents(uploaded_files, section_titles, project_name, report_date_str)
                    output = io.BytesIO()
                    merged_doc.save(output)
                    
                    st.success(f"✅ รวมไฟล์เรียบร้อย! พบ {file_count} ส่วน")
                    st.download_button(
                        label="📥 ดาวน์โหลดไฟล์รายงาน (.docx)",
                        data=output.getvalue(),
                        file_name=f"รายงานออกแบบ_{project_name}.docx" if project_name else "รายงานออกแบบโครงสร้างชั้นทาง.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
