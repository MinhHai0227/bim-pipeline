# Khảo sát hiện trạng file BIM phục vụ vận hành Digital Twin

## 1) Bối cảnh và mục tiêu

Là PO Digital Twin, nhóm TTS thực hiện khảo sát hiện trạng file BIM từ giai đoạn xây dựng để xác định các vấn đề dữ liệu trước khi đưa vào vận hành Digital Twin.

Mục tiêu chính:

1. Thu thập và phân loại mẫu dữ liệu BIM hiện có.
2. Nhận diện vấn đề dữ liệu phổ biến ảnh hưởng đến vận hành.
3. Kiểm tra sơ bộ object, metadata, IFC Class, Property Set.
4. Xác định bộ field tối thiểu cho asset vận hành.
5. Khởi tạo cấu trúc tài liệu bàn giao và báo cáo.

## 2) AC1 - Thu thập tối thiểu 2-3 file mẫu/case mẫu BIM/IFC/Revit/Navisworks

### 2.1 Kết quả thu thập thực tế trong `data/`

| STT | File                             | Định dạng | Schema | Dung lượng (bytes) | Ghi chú                      |
| --- | -------------------------------- | --------- | ------ | -----------------: | ---------------------------- |
| 1   | `AC20-FZK-Haus.ifc`              | IFC       | IFC4   |          2,570,803 | Mẫu kiến trúc (ArchiCAD/FZK) |
| 2   | `Ifc2x3_Duplex_Architecture.ifc` | IFC       | IFC2X3 |          2,419,670 | Mẫu kiến trúc (Revit Export) |
| 3   | `Ifc2x3_Duplex_Mechanical.ifc`   | IFC       | IFC2X3 |          8,937,108 | Mẫu MEP (Revit Export)       |

## 3) AC2 - Liệt kê vấn đề phổ biến

Các vấn đề dữ liệu thường gặp trong mẫu đang có và bối cảnh BIM bàn giao vận hành:

1. Metadata thừa: nhiều thuộc tính phục vụ thiết kế nhưng không phục vụ vận hành.
2. Thiếu vai trò tài sản: chưa thống nhất cách phân biệt đối tượng asset cần bảo trì.
3. Thiếu thông tin vận hành: thiếu hoặc không đồng nhất các field như `tag`, `system`, `manufacturer`, `model`.
4. Không đồng nhất chuẩn dữ liệu: tên Property Set khác nhau giữa nguồn ArchiCAD và Revit.
5. Rủi ro phân loại: IFC Class đúng kỹ thuật nhưng chưa map rõ sang danh mục asset vận hành.
6. Rủi ro vị trí: cần kiểm tra sâu hơn quan hệ `Storey/Space` để định vị asset.

## 4) AC3 - Bảng phân loại vấn đề theo nhóm

| Nhóm vấn đề      | Hiện trạng sơ bộ                                                    | Mức ảnh hưởng vận hành | Hướng xử lý                                         |
| ---------------- | ------------------------------------------------------------------- | ---------------------- | --------------------------------------------------- |
| Geometry         | Mô hình có số lượng entity lớn, chưa kiểm tra chi tiết lỗi hình học | Trung bình             | Kiểm tra geometry validity bằng tool chuyên dụng    |
| Metadata         | Có Property Set nhưng độ đầy đủ field chưa được đo completeness     | Cao                    | Chuẩn hóa dictionary và kiểm tra tỷ lệ điền đủ      |
| Classification   | IFC Class đa dạng nhưng chưa map chuẩn sang taxonomy vận hành       | Cao                    | Lập bảng map `ifc_class -> asset_category`          |
| Asset Code       | Chưa xác nhận độ đầy đủ `tag/mark/asset_code` trên từng nhóm asset  | Cao                    | Bắt buộc field định danh trong checklist nghiệm thu |
| Location         | Chưa kiểm tra đầy đủ phân cấp spatial đến `Storey/Space`            | Cao                    | Đối soát containment theo từng asset                |
| Maintenance Info | Thiếu kiểm tra sâu các field O&M (warranty, serial, install date)   | Rất cao                | Bổ sung field tối thiểu và ngưỡng completeness      |

## 5) AC4 - Danh sách metadata cần giữ lại/chuẩn hóa/bổ sung/loại bỏ

### 5.1 Metadata cần giữ lại (bắt buộc)

1. `asset_guid` (`IfcRoot.GlobalId`)
2. `asset_name` (`IfcRoot.Name`)
3. `ifc_class`
4. `asset_type`
5. `location` (`site/building/storey/space`)
6. `system_name` (đặc biệt cho MEP)
7. `tag_or_mark`

### 5.2 Metadata cần chuẩn hóa

1. Chuẩn tên Property Set giữa ArchiCAD/Revit.
2. Chuẩn đơn vị đo và kiểu dữ liệu field số.
3. Chuẩn mã phân loại asset và quy tắc đặt tên.
4. Chuẩn format giá trị định danh (`tag`, `code`, `system`).

### 5.3 Metadata cần bổ sung

1. `manufacturer`
2. `model_number`
3. `serial_number`
4. `install_date`
5. `warranty_end`
6. `om_manual_link`

### 5.4 Metadata cân nhắc loại bỏ khỏi bộ bàn giao vận hành

1. Thuộc tính chỉ phục vụ mô hình hóa thiết kế, không phục vụ khai thác/bảo trì.
2. Thuộc tính trùng nghĩa, khác tên giữa nhiều Pset.
3. Thuộc tính rỗng lặp lại với tỷ lệ cao và không có kế hoạch bổ sung.

## 6) Kiểm tra sơ bộ object, IFC Class và Property Set

### 6.1 Quy mô mô hình

| File                             | Tổng entity IFC | Có Property Set |
| -------------------------------- | --------------: | --------------- |
| `AC20-FZK-Haus.ifc`              |          44,249 | Có              |
| `Ifc2x3_Duplex_Architecture.ifc` |          38,898 | Có              |
| `Ifc2x3_Duplex_Mechanical.ifc`   |         155,212 | Có              |

### 6.2 IFC Class nghiệp vụ nổi bật

1. `AC20-FZK-Haus.ifc`: `IFCMEMBER`, `IFCWALLSTANDARDCASE`, `IFCWINDOW`, `IFCSPACE`, `IFCDOOR`.
2. `Ifc2x3_Duplex_Architecture.ifc`: `IFCFURNISHINGELEMENT`, `IFCWALLSTANDARDCASE`, `IFCWINDOW`, `IFCSPACE`, `IFCSLAB`, `IFCDOOR`.
3. `Ifc2x3_Duplex_Mechanical.ifc`: `IFCFLOWSEGMENT`, `IFCFLOWFITTING`, `IFCFLOWCONTROLLER`, `IFCFLOWMOVINGDEVICE`, `IFCSPACE`.

### 6.3 Property Set nổi bật

1. ArchiCAD model: `AC_Pset_Name`, `ArchiCADProperties`, `Pset_BeamCommon`, `Pset_WallCommon`.
2. Revit Architecture: `PSet_Revit_Other`, `PSet_Revit_Constraints`, `PSet_Revit_Phasing`, `PSet_Revit_Dimensions`.
3. Revit Mechanical: `PSet_Revit_Constraints`, `PSet_Revit_Identity Data`, `PSet_Revit_Mechanical`, `PSet_Revit_Dimensions`.

## 7) Checklist khảo sát dữ liệu BIM (dùng triển khai)

- [x] Kiểm tra tồn tại file và dung lượng.
- [x] Xác định schema IFC.
- [x] Đếm tổng số entity IFC.
- [x] Kiểm tra hiện diện IFC Class và Property Set chính.
- [ ] Kiểm tra chi tiết phân cấp spatial (`Site > Building > Storey > Space`).
- [ ] Kiểm tra uniqueness `GlobalId`.
- [ ] Đo completeness bộ field tối thiểu theo nhóm asset.
- [ ] Kiểm tra chuẩn hóa đơn vị, kiểu dữ liệu, naming convention.
- [ ] Kiểm tra file Revit/Navisworks và mapping liên nền tảng.

## 8) Bộ field tối thiểu cho asset vận hành

| Nhóm      | Field                                           | Bắt buộc          |
| --------- | ----------------------------------------------- | ----------------- |
| Định danh | `asset_guid`, `asset_name`                      | Có                |
| Phân loại | `ifc_class`, `asset_type`                       | Có                |
| Vị trí    | `site/building/storey/space`                    | Có                |
| Vận hành  | `system_name`, `tag_or_mark`                    | Có (đặc biệt MEP) |
| Kỹ thuật  | `manufacturer`, `model_number`, `serial_number` | Nên có            |
| Bảo trì   | `install_date`, `warranty_end`                  | Nên có            |
| Tài liệu  | `om_manual_link`                                | Nên có            |

Ngưỡng completeness đề xuất:

1. Nhóm bắt buộc lõi đạt >= 98%.
2. Nhóm vận hành MEP đạt >= 95%.
3. Nhóm kỹ thuật/bảo trì đạt >= 90%.
