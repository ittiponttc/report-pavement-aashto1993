# -*- coding: utf-8 -*-
"""
โปรแกรมรวมไฟล์ Word รายงานออกแบบโครงสร้างชั้นทาง
Pavement Design Report Merger
Version 2.0

โดย: ภาควิชาครุศาสตร์โยธา มจพ.
"""

import streamlit as st
import os
import tempfile
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docxcompose.composer import Composer
import io

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง",
    page_icon="🛣️",
    layout="wide"
)

# CSS สำหรับตกแต่งหน้าเว็บ
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
    .file-section-sub {
        background-color: #EDF2F7;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 5px 0 5px 20px;
        border-left: 3px solid #A0AEC0;
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
    .warning-box {
        background-color: #FEFCBF;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #D69E2E;
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
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)


def copy_table(source_table, target_doc):
    """คัดลอกตารางจากเอกสารต้นทางไปยังเอกสารปลายทาง"""
    rows = len(source_table.rows)
    cols = len(source_table.columns)
    new_table = target_doc.add_table(rows=rows, cols=cols)
    
    for i, row in enumerate(source_table.rows):
        for j, cell in enumerate(row.cells):
            new_cell = new_table.rows[i].cells[j]
            for para in cell.paragraphs:
                if para.text.strip():
                    new_para = new_cell.paragraphs[0] if new_cell.paragraphs else new_cell.add_paragraph()
                    new_para.clear()
                    for run in para.runs:
                        new_run = new_para.add_run(run.text)
                        if run.font.bold:
                            new_run.font.bold = run.font.bold
                        if run.font.size:
                            new_run.font.size = run.font.size
                        if run.font.name:
                            new_run.font.name = run.font.name
    
    return new_table


def merge_documents(uploaded_files, section_titles, project_name, report_date):
    """รวมเอกสารทั้งหมดเป็นไฟล์เดียว (รองรับรูปภาพ ตาราง)"""
    
    # สร้างเอกสารหลัก
    merged_doc = Document()
    section = merged_doc.sections[0]
    set_page_margins(section)
    
    # สร้างหน้าปก
    title_para = merged_doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run("\n\n\n\n\n")
    
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
    
    merged_doc.add_paragraph()
    
    # สร้างรายการสารบัญ
    toc_items = []
    section_num = 1
    for key, file in uploaded_files.items():
        if file is not None:
            toc_items.append((section_num, section_titles[key]))
            section_num += 1
    
    for num, title in toc_items:
        toc_para = merged_doc.add_paragraph()
        toc_run = toc_para.add_run(f"{num}. {title}")
        set_thai_font(toc_run, font_size=15)
    
    merged_doc.add_page_break()
    
    # บันทึกเอกสารหลักชั่วคราว
    temp_main = io.BytesIO()
    merged_doc.save(temp_main)
    temp_main.seek(0)
    
    # โหลดเอกสารหลักใหม่สำหรับ Composer
    master_doc = Document(temp_main)
    composer = Composer(master_doc)
    
    # รวมเนื้อหาจากแต่ละไฟล์
    section_num = 1
    for key, file in uploaded_files.items():
        if file is not None:
            file_bytes = file.read()
            file.seek(0)
            
            # สร้างเอกสารหัวข้อ
            header_doc = Document()
            
            # หัวข้อส่วน
            section_title = header_doc.add_paragraph()
            section_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
            section_run = section_title.add_run(f"{section_num}. {section_titles[key]}")
            set_thai_font(section_run, font_size=18)
            section_run.font.bold = True
            
            header_doc.add_paragraph()
            
            # บันทึกหัวข้อชั่วคราว
            temp_header = io.BytesIO()
            header_doc.save(temp_header)
            temp_header.seek(0)
            
            # เพิ่มหัวข้อ
            composer.append(Document(temp_header))
            
            # เพิ่มเนื้อหาจากไฟล์ต้นฉบับ
            source_doc = Document(io.BytesIO(file_bytes))
            composer.append(source_doc)
            
            section_num += 1
    
    return composer.doc


def main():
    # หัวข้อหลัก
    st.markdown('<div class="main-header">🛣️ โปรแกรมรวมรายงานออกแบบโครงสร้างชั้นทาง</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pavement Structure Design Report Merger v2.0</div>', unsafe_allow_html=True)
    
    # ข้อมูลโครงการ
    st.markdown("### 📋 ข้อมูลโครงการ")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("ชื่อโครงการ", placeholder="กรอกชื่อโครงการ")
    with col2:
        report_date = st.date_input("วันที่รายงาน", datetime.now())
        report_date_str = report_date.strftime("%d/%m/%Y")
    
    st.markdown("---")
    
    # คำอธิบายส่วนต่างๆ (ปรับปรุงใหม่)
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
    st.info("💡 อัปโหลดไฟล์ Word (.docx) สำหรับแต่ละส่วนของรายงาน ไฟล์ที่มีเครื่องหมาย (ถ้ามี) สามารถเว้นว่างได้")
    
    uploaded_files = {}
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 1: Truck Factor
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">📊 1. การคำนวณ Truck Factor</div>', unsafe_allow_html=True)
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**การคำนวณ Truck Factor** (ถ้ามี)")
    uploaded_files['truck_factor'] = st.file_uploader(
        "เลือกไฟล์ Truck Factor",
        type=['docx'],
        key='truck_factor',
        help="ไฟล์รายงานการคำนวณ Truck Factor"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 2: ESALs (แยกเป็น 2 ประเภท)
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">📈 2. การคำนวณ ESALs (Equivalent Single Axle Loads)</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="file-section">', unsafe_allow_html=True)
        st.markdown("**2.1 ESALs สำหรับผิวทางลาดยาง** (Flexible Pavement)")
        uploaded_files['esals_ac'] = st.file_uploader(
            "เลือกไฟล์ ESALs ผิวทางลาดยาง",
            type=['docx'],
            key='esals_ac',
            help="ไฟล์รายงานการคำนวณ ESALs สำหรับผิวทางลาดยาง (AC)"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="file-section">', unsafe_allow_html=True)
        st.markdown("**2.2 ESALs สำหรับผิวทางคอนกรีต** (Rigid Pavement)")
        uploaded_files['esals_concrete'] = st.file_uploader(
            "เลือกไฟล์ ESALs ผิวทางคอนกรีต",
            type=['docx'],
            key='esals_concrete',
            help="ไฟล์รายงานการคำนวณ ESALs สำหรับผิวทางคอนกรีต"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 3: การวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">🔬 3. การวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์</div>', unsafe_allow_html=True)
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**การวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์**")
    uploaded_files['cbr_analysis'] = st.file_uploader(
        "เลือกไฟล์วิเคราะห์ CBR",
        type=['docx'],
        key='cbr_analysis',
        help="ไฟล์รายงานการวิเคราะห์ค่า CBR ที่เปอร์เซ็นต์ไทล์ (Percentile Analysis)"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 4: การออกแบบผิวทางลาดยาง
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">🛤️ 4. การออกแบบผิวทางลาดยาง (Flexible Pavement)</div>', unsafe_allow_html=True)
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**การออกแบบผิวทางลาดยาง (AC)**")
    uploaded_files['ac_design'] = st.file_uploader(
        "เลือกไฟล์ออกแบบ AC",
        type=['docx'],
        key='ac_design',
        help="ไฟล์รายงานการออกแบบผิวทางแอสฟัลต์ตามวิธี AASHTO 1993"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 5: การออกแบบผิวทางคอนกรีต (แยกเป็น 2 ประเภท)
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">🏗️ 5. การออกแบบผิวทางคอนกรีต (Rigid Pavement)</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="file-section">', unsafe_allow_html=True)
        st.markdown("**5.1 การออกแบบ JPCP/JRCP**")
        st.caption("Jointed Plain/Reinforced Concrete Pavement")
        uploaded_files['jpcp_jrcp_design'] = st.file_uploader(
            "เลือกไฟล์ออกแบบ JPCP/JRCP",
            type=['docx'],
            key='jpcp_jrcp_design',
            help="ไฟล์รายงานการออกแบบผิวทาง JPCP หรือ JRCP"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="file-section">', unsafe_allow_html=True)
        st.markdown("**5.2 การออกแบบ CRCP**")
        st.caption("Continuously Reinforced Concrete Pavement")
        uploaded_files['crcp_design'] = st.file_uploader(
            "เลือกไฟล์ออกแบบ CRCP",
            type=['docx'],
            key='crcp_design',
            help="ไฟล์รายงานการออกแบบผิวทาง CRCP"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 6: Corrected Modulus of Subgrade Reaction (แยกเป็น 2 ประเภท)
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">📐 6. การคำนวณ Corrected Modulus of Subgrade Reaction (k-value)</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="file-section">', unsafe_allow_html=True)
        st.markdown("**6.1 k-value สำหรับ JPCP/JRCP**")
        uploaded_files['k_value_jpcp_jrcp'] = st.file_uploader(
            "เลือกไฟล์ k-value JPCP/JRCP",
            type=['docx'],
            key='k_value_jpcp_jrcp',
            help="ไฟล์รายการคำนวณ Corrected k-value สำหรับ JPCP/JRCP"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="file-section">', unsafe_allow_html=True)
        st.markdown("**6.2 k-value สำหรับ CRCP**")
        uploaded_files['k_value_crcp'] = st.file_uploader(
            "เลือกไฟล์ k-value CRCP",
            type=['docx'],
            key='k_value_crcp',
            help="ไฟล์รายการคำนวณ Corrected k-value สำหรับ CRCP"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # ส่วนที่ 7: การประมาณราคา
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">💰 7. การประมาณราคาค่าก่อสร้าง</div>', unsafe_allow_html=True)
    st.markdown('<div class="file-section">', unsafe_allow_html=True)
    st.markdown("**การประมาณราคาค่าก่อสร้าง** (ถ้ามี)")
    uploaded_files['cost_estimate'] = st.file_uploader(
        "เลือกไฟล์ประมาณราคา",
        type=['docx'],
        key='cost_estimate',
        help="ไฟล์รายงานการประมาณราคาค่าก่อสร้าง"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════
    # แสดงสถานะไฟล์ที่อัปโหลด
    # ═══════════════════════════════════════════════════════════════
    st.markdown("### 📊 สถานะไฟล์ที่อัปโหลด")
    
    file_count = sum(1 for f in uploaded_files.values() if f is not None)
    
    # แสดงสถานะแบบตาราง
    status_data = {
        'หมวด': [
            '1. Truck Factor',
            '2.1 ESALs (Flexible)',
            '2.2 ESALs (Rigid)',
            '3. CBR Analysis',
            '4. AC Design',
            '5.1 JPCP/JRCP',
            '5.2 CRCP',
            '6.1 k-value (JPCP/JRCP)',
            '6.2 k-value (CRCP)',
            '7. Cost Estimate'
        ],
        'สถานะ': []
    }
    
    file_keys = ['truck_factor', 'esals_ac', 'esals_concrete', 'cbr_analysis', 'ac_design', 
                 'jpcp_jrcp_design', 'crcp_design', 'k_value_jpcp_jrcp', 
                 'k_value_crcp', 'cost_estimate']
    
    for key in file_keys:
        if uploaded_files[key] is not None:
            status_data['สถานะ'].append('✅ อัปโหลดแล้ว')
        else:
            status_data['สถานะ'].append('⬜ ยังไม่อัปโหลด')
    
    # แสดงในรูปแบบ 3 คอลัมน์
    cols = st.columns(3)
    for i, (name, status) in enumerate(zip(status_data['หมวด'], status_data['สถานะ'])):
        with cols[i % 3]:
            if '✅' in status:
                st.success(f"{name}: {status}")
            else:
                st.warning(f"{name}: {status}")
    
    st.markdown(f"### 📈 อัปโหลดแล้ว: **{file_count}** จาก **10** ไฟล์")
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════
    # ปุ่มรวมไฟล์
    # ═══════════════════════════════════════════════════════════════
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        merge_button = st.button("🔄 รวมไฟล์และสร้างรายงาน", use_container_width=True)
    
    if merge_button:
        if file_count == 0:
            st.error("❌ กรุณาอัปโหลดไฟล์อย่างน้อย 1 ไฟล์")
        else:
            with st.spinner("กำลังรวมไฟล์และสร้างรายงาน..."):
                try:
                    merged_doc = merge_documents(
                        uploaded_files,
                        section_titles,
                        project_name,
                        report_date_str
                    )
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        base_filename = "รายงานออกแบบโครงสร้างชั้นทาง"
                        if project_name:
                            base_filename = f"รายงานออกแบบ_{project_name.replace(' ', '_')}"
                        
                        docx_path = os.path.join(temp_dir, f"{base_filename}.docx")
                        
                        merged_doc.save(docx_path)
                        
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.success(f"✅ รวมไฟล์เรียบร้อยแล้ว! ({file_count} ไฟล์)")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown("### 📥 ดาวน์โหลดรายงาน")
                        
                        with open(docx_path, 'rb') as f:
                            docx_data = f.read()
                        st.download_button(
                            label="📄 ดาวน์โหลดไฟล์ Word (.docx)",
                            data=docx_data,
                            file_name=f"{base_filename}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                    st.exception(e)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #718096; font-size: 14px;">
        <p>พัฒนาโดย ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม</p>
        <p>มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ</p>
        <p>© 2025 - Pavement Design Report Merger v2.0</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
