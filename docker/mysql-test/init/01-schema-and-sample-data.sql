-- Synthetic MES-like test schema. All rows are fictional.
CREATE TABLE production_line (
  line_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '产线主键',
  line_code VARCHAR(30) NOT NULL UNIQUE COMMENT '产线编码',
  line_name VARCHAR(100) NOT NULL COMMENT '产线名称',
  workshop VARCHAR(80) NOT NULL COMMENT '所属车间',
  enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB COMMENT='生产线基础信息';

CREATE TABLE material (
  material_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '物料主键',
  material_code VARCHAR(40) NOT NULL UNIQUE COMMENT '物料编码',
  material_name VARCHAR(120) NOT NULL COMMENT '物料名称',
  material_type VARCHAR(40) NOT NULL COMMENT '物料类别',
  unit VARCHAR(12) NOT NULL COMMENT '计量单位',
  safety_stock DECIMAL(14,3) NOT NULL DEFAULT 0 COMMENT '安全库存'
) ENGINE=InnoDB COMMENT='物料主数据';

CREATE TABLE equipment (
  equipment_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '设备主键',
  equipment_code VARCHAR(40) NOT NULL UNIQUE COMMENT '设备编码',
  equipment_name VARCHAR(120) NOT NULL COMMENT '设备名称',
  line_id BIGINT NULL COMMENT '所属产线',
  equipment_status VARCHAR(20) NOT NULL DEFAULT '运行' COMMENT '设备状态',
  commissioned_on DATE NULL COMMENT '投产日期',
  CONSTRAINT fk_equipment_line FOREIGN KEY (line_id) REFERENCES production_line(line_id)
) ENGINE=InnoDB COMMENT='生产设备台账';

CREATE TABLE production_order (
  order_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '生产订单主键',
  order_no VARCHAR(40) NOT NULL UNIQUE COMMENT '生产订单号',
  material_id BIGINT NOT NULL COMMENT '产品物料',
  line_id BIGINT NOT NULL COMMENT '生产产线',
  plan_qty INT NOT NULL COMMENT '计划数量',
  completed_qty INT NOT NULL DEFAULT 0 COMMENT '完工数量',
  planned_start DATETIME NOT NULL COMMENT '计划开始时间',
  order_status VARCHAR(20) NOT NULL DEFAULT '待开工' COMMENT '订单状态',
  CONSTRAINT fk_order_material FOREIGN KEY (material_id) REFERENCES material(material_id),
  CONSTRAINT fk_order_line FOREIGN KEY (line_id) REFERENCES production_line(line_id)
) ENGINE=InnoDB COMMENT='生产订单';

CREATE TABLE quality_inspection (
  inspection_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '检验记录主键',
  inspection_no VARCHAR(40) NOT NULL UNIQUE COMMENT '检验单号',
  order_id BIGINT NOT NULL COMMENT '关联生产订单',
  inspected_qty INT NOT NULL COMMENT '检验数量',
  passed_qty INT NOT NULL COMMENT '合格数量',
  inspected_at DATETIME NOT NULL COMMENT '检验时间',
  inspector VARCHAR(60) NOT NULL COMMENT '检验员',
  CONSTRAINT fk_inspection_order FOREIGN KEY (order_id) REFERENCES production_order(order_id)
) ENGINE=InnoDB COMMENT='质量检验记录';

CREATE TABLE defect_record (
  defect_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '不良记录主键',
  inspection_id BIGINT NOT NULL COMMENT '关联检验记录',
  defect_code VARCHAR(30) NOT NULL COMMENT '不良代码',
  defect_desc VARCHAR(200) NOT NULL COMMENT '不良描述',
  defect_qty INT NOT NULL DEFAULT 1 COMMENT '不良数量',
  CONSTRAINT fk_defect_inspection FOREIGN KEY (inspection_id) REFERENCES quality_inspection(inspection_id)
) ENGINE=InnoDB COMMENT='质量不良明细';

CREATE VIEW v_production_order_progress AS
SELECT order_no, plan_qty, completed_qty,
       ROUND(completed_qty / NULLIF(plan_qty, 0) * 100, 2) AS completion_rate,
       order_status
FROM production_order
;

INSERT INTO production_line (line_code,line_name,workshop) VALUES
('LED-L01','LED封装一线','封装一车间'),
('LED-L02','LED封装二线','封装一车间'),
('LED-L03','Mini LED试制线','研发试制车间');

INSERT INTO material (material_code,material_name,material_type,unit,safety_stock) VALUES
('LED-2835-W','2835白光LED','成品','KPCS',500.000),
('LED-3030-R','3030红光LED','成品','KPCS',300.000),
('MAT-CHIP-01','蓝光芯片','原材料','KPCS',1200.000),
('MAT-PKG-02','封装支架','原材料','KPCS',800.000);

INSERT INTO equipment (equipment_code,equipment_name,line_id,equipment_status,commissioned_on) VALUES
('EQ-DIE-001','固晶机-001',1,'运行','2024-03-15'),
('EQ-WIRE-002','焊线机-002',1,'运行','2023-11-20'),
('EQ-TEST-003','分光编带机-003',2,'维护','2022-08-01'),
('EQ-MINI-004','Mini LED检测设备',3,'运行','2025-02-10');

INSERT INTO production_order (order_no,material_id,line_id,plan_qty,completed_qty,planned_start,order_status) VALUES
('MO-2026-11001',1,1,100000,85000,'2026-11-20 08:00:00','生产中'),
('MO-2026-11002',2,2,80000,80000,'2026-11-19 08:00:00','已完工'),
('MO-2026-11003',1,1,120000,0,'2026-11-23 08:00:00','待开工'),
('MO-2026-11004',3,3,20000,12000,'2026-11-21 09:00:00','生产中');

INSERT INTO quality_inspection (inspection_no,order_id,inspected_qty,passed_qty,inspected_at,inspector) VALUES
('QI-2026-001',1,20000,19820,'2026-11-21 16:30:00','检验员A'),
('QI-2026-002',2,30000,29760,'2026-11-20 15:20:00','检验员B'),
('QI-2026-003',4,5000,4920,'2026-11-22 10:15:00','检验员C');

INSERT INTO defect_record (inspection_id,defect_code,defect_desc,defect_qty) VALUES
(1,'D-001','亮度偏低',90),
(1,'D-002','外观划伤',110),
(2,'D-003','色温偏差',240),
(3,'D-004','焊线异常',80);
