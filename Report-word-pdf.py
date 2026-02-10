# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger
Version 2.1 (Hotfix for Python 3.13)

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

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide"
)

# CSS สำหรับตกแต่งหน้าเว็บ (คงเดิมตามต้นฉบับ)
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
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)

def set_thai_font(run, font_name="TH Sarabun New", font_size=15):
    """ตั้งค่าฟอนต์ไทยและขนาด"""
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
    """ตั้งค่าหน้ากระดาษ A4 แนวตั้ง กั้นหน้า-หลัง 2.5 cm"""
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.orientation = WD_ORIENT.PORTRAIT
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)

def append_document(master_doc, source_doc):
    """คัดลอกเนื้อหาจากเอกสารต้นทางไปยังเอกสารปลายทาง"""
    # คัดลอก relationships สำหรับรูปภาพ
    for rel_id, rel in source_doc.part.rels.items():
        if "image" in rel.reltype:
            try:
                master_doc.part.relate_to(rel.target_part, rel.reltype)
            except:
                pass
    
    # คัดลอก elements จาก body
    for element in source_doc.element.body:
        if element.tag.endswith('sectPr'):
            continue
        new_element = deepcopy(element)
        master_doc.element.body.append(new_element)

def merge_documents(uploaded_files, section_titles, project_name, report_date):
    """รวมเอกสารทั้งหมดเป็นไฟล์เดียว"""
    merged_doc = Document()
    section = merged_doc.sections[0]
    set_page_margins(section)
    
    # หน้าปก
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
    
    # สารบัญ
    toc_title = merged_doc.add_paragraph()
    toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    toc_run = toc_title.add_run("สารบัญ")
    set_thai_font(toc_run, font_size=18)
    toc_run.font.bold = True
    
    section_num = 1
    for key, file in uploaded_files.items():
        if file is not None:
            toc_para = merged_doc.add_paragraph()
            toc_run = toc_para.add_run(f"{section_num}. {section_titles[key]}")
            set_thai_font(toc_run, font_size=15)
            section_num += 1
    
    merged_doc.add_page_break()
    
    # รวมเนื้อหา
    section_num = 1
    for key, file in uploaded_files.items():
        if file is not None:
            file_bytes = file.read()
            file.seek(0)
            
            section_title_para = merged_doc.add_paragraph()
            section_run = section_title_para.add_run(f"{section_num}. {section_titles[key]}")
            set_thai_font(section_run, font_size=18)
            section_run.font.bold = True
            
            source_doc = Document(io.BytesIO(file_bytes))
            append_document(merged_doc, source_doc)
            merged_doc.add_page_break()
            section_num += 1
            
    return merged_doc

def main():
    st.markdown('<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pavement Structure Design Report Merger v2.1</div>', unsafe_allow_html=True)
    
    st.markdown("### 📋 ข้อมูลโครงการ")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("ชื่อโครงการ", placeholder="กรอกชื่อโครงการ")
    with col2:
        report_date = st.date_input("วันที่รายงาน", datetime.now())
        report_date_str = report_date.strftime("%d/%m/%Y")
    
    st.markdown("---")
    
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
    
    st.markdown("### 📁 อัปโหลดไฟล์รายงาน")
    uploaded_files = {}
    
    # สร้าง UI อัปโหลดไฟล์ตามลำดับเดิม
    sections = [
        ("📊 1. การคำนวณ Truck Factor", ['truck_factor']),
        ("📈 2. การคำนวณ ESALs", ['esals_ac', 'esals_concrete']),
        ("🔬 3. การวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์", ['cbr_analysis']),
        ("🛤️ 4. การออกแบบผิวทางลาดยาง", ['ac_design']),
        ("🏗️ 5. การออกแบบผิวทางคอนกรีต", ['jpcp_jrcp_design', 'crcp_design']),
        ("📐 6. การคำนวณ Corrected k-value", ['k_value_jpcp_jrcp', 'k_value_crcp']),
        ("💰 7. การประมาณราคาค่าก่อสร้าง", ['cost_estimate'])
    ]

    for label, keys in sections:
        st.markdown(f'<div class="section-header">{label}</div>', unsafe_allow_html=True)
        cols = st.columns(len(keys))
        for i, key in enumerate(keys):
            with cols[i]:
                uploaded_files[key] = st.file_uploader(f"เลือกไฟล์ {section_titles[key]}", type=['docx'], key=key)

    st.markdown("---")
    file_count = sum(1 for f in uploaded_files.values() if f is not None)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 รวมไฟล์และสร้างรายงาน", use_container_width=True):
            if file_count == 0:
                st.error("❌ กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
            else:
                with st.spinner("กำลังรวมไฟล์..."):
                    try:
                        merged_doc = merge_documents(uploaded_files, section_titles, project_name, report_date_str)
                        output = io.BytesIO()
                        merged_doc.save(output)
                        
                        st.success(f"✅ รวมไฟล์เรียบร้อยแล้ว! ({file_count} ไฟล์)")
                        st.download_button(
                            label="📄 ดาวน์โหลดไฟล์ Word (.docx)",
                            data=output.getvalue(),
                            file_name=f"รายงานออกแบบ_{project_name}.docx" if project_name else "รายงานออกแบบโครงสร้างชั้นทาง.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")

    st.markdown("---")
    st.markdown('<div style="text-align: center; color: #718096; font-size: 14px;">© 2025 - Pavement Design Report Merger v2.1</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
