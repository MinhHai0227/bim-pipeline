# Khảo sát hiện trạng file BIM phục vụ vận hành Digital Twin

## 1) Mục tiêu và phạm vi

Tài liệu này dùng để khởi tạo bộ hồ sơ khảo sát dữ liệu BIM trước khi đưa vào BIM Pipeline và Digital Twin. Phạm vi bao gồm file IFC hiện có trong repo, file IFC xuất từ Revit/Tekla/ArchiCAD, và các case cần bổ sung từ Revit/Navisworks native nếu dự án cung cấp.

Mục tiêu chính:

1. Thu thập file/case mẫu BIM/IFC/Revit/Navisworks.
2. Xây dựng checklist khảo sát dữ liệu BIM.
3. Kiểm tra sơ bộ object, metadata, IFC Class, Property Set.
4. Xác định field tối thiểu cho asset vận hành.
5. Khởi tạo tài liệu bàn giao và cấu trúc báo cáo.
6. Phân tích lỗi phổ biến và rule dữ liệu ban đầu.

## 2) Thu thập file/case mẫu

### 2.1 File mẫu hiện có trong `data/raw`

| STT | File | Nguồn/Tool thể hiện trong IFC header | Định dạng | Schema | Dung lượng bytes | Tổng entity IFC | Trạng thái |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| 1 | `AC20-FZK-Haus.ifc` | GRAPHISOFT ArchiCAD 20 | IFC | IFC4 | 2,570,803 | 44,249 | Đã thu thập |
| 2 | `Ifc2x3_Duplex_Architecture.ifc` | Autodesk Revit Architecture 2011 | IFC export | IFC2X3 | 2,419,670 | 38,898 | Đã thu thập |
| 3 | `Ifc2x3_Duplex_Mechanical.ifc` | Autodesk Revit MEP 2011 | IFC export | IFC2X3 | 8,937,108 | 155,212 | Đã thu thập |
| 4 | `CuaDai_BIM_Mis 2.ifc` | Tekla Structures 2017 | IFC export | IFC2X3 | 16,027,122 | 192,562 | Đã thu thập |

### 2.2 Case còn thiếu cần bổ sung

| Case cần có | Mục đích khảo sát | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| File Revit native `.rvt` | Kiểm tra metadata trước khi export IFC | Chưa có | Cần lấy từ dự án hoặc dùng file mẫu có quyền chia sẻ |
| File Navisworks `.nwd/.nwc` | Kiểm tra model coordination và metadata tổng hợp | Chưa có | Cần xác định tool/API chuyển đổi phù hợp |
| IFC kiến trúc | Kiểm tra spatial, door/window/room | Đã có | `AC20-FZK-Haus.ifc`, `Ifc2x3_Duplex_Architecture.ifc` |
| IFC MEP | Kiểm tra system, equipment, maintenance field | Đã có | `Ifc2x3_Duplex_Mechanical.ifc` |
| IFC kết cấu/Tekla | Kiểm tra assembly, beam, plate, column | Đã có | `CuaDai_BIM_Mis 2.ifc` |

## 3) Checklist khảo sát dữ liệu BIM

### 3.1 Tiếp nhận file

- [x] Kiểm tra file tồn tại trong thư mục nguồn.
- [x] Ghi nhận tên file, định dạng, dung lượng, nguồn/tool export nếu có.
- [x] Xác định schema IFC.
- [ ] Ghi nhận mã dự án, discipline, gói thầu, phiên bản bàn giao.
- [ ] Xác định file native tương ứng nếu có: Revit/Navisworks/Tekla/ArchiCAD.

### 3.2 Kiểm tra cấu trúc và object

- [x] Đếm tổng entity IFC.
- [x] Đếm `IfcProduct`.
- [x] Liệt kê IFC Class nổi bật theo file.
- [x] Loại trừ sơ bộ object không phải asset vận hành: `IfcAnnotation`, `IfcOpeningElement`, `IfcVirtualElement`.
- [ ] Kiểm tra geometry validity bằng tool chuyên dụng nếu cần viewer/coordination.
- [ ] Kiểm tra object bị duplicate hoặc object không có hình học.

### 3.3 Kiểm tra metadata và Property Set

- [x] Liệt kê Property Set nổi bật.
- [x] Kiểm tra field lõi: `GlobalId`, `Name`, `Tag`, `Floor`, `Room`.
- [x] Kiểm tra field vận hành theo alias hiện có: `AssetIdentifier`, `Manufacturer`, `Model`, `SerialNumber`, `Status`, `System`.
- [ ] Đo completeness theo từng nhóm asset vận hành.
- [ ] Kiểm tra field sai kiểu dữ liệu, sai đơn vị, sai format ngày tháng.
- [ ] Kiểm tra metadata rỗng, placeholder, trùng nghĩa khác tên.

### 3.4 Kiểm tra phân loại, mã hóa, vị trí

- [ ] Map `ifc_class` sang `asset_type` vận hành.
- [ ] Map system thô từ BIM sang taxonomy `ARCH`, `STR`, `HVAC`, `EL`, `PLB`, `FF`, `SEC`, `LIFT`, `BMS`.
- [ ] Kiểm tra uniqueness `GlobalId`.
- [ ] Kiểm tra completeness `Asset ID`/`Tag`.
- [ ] Kiểm tra phân cấp vị trí `Site > Building > Storey > Space/Zone`.
- [ ] Đánh dấu asset thiếu floor/room để bổ sung.

### 3.5 Đầu ra khảo sát

- [x] Tài liệu khảo sát hiện trạng.
- [x] Bảng mapping BIM Property -> Digital Twin Property: `docs/bim-dt-property-mapping.csv`.
- [x] Tài liệu chuẩn handover: `docs/BIM-Handover-Standard-for-Digital-Twin-v1.md`.
- [ ] Báo cáo completeness theo file và theo nhóm asset.
- [ ] File issue log dạng CSV/JSON để đưa vào BIM Pipeline.

## 4) Phân tích sơ bộ file mẫu

### 4.1 Tổng quan object/product

| File | Schema | `IfcProduct` | Product sau loại trừ | Asset vận hành ứng viên | Nhận xét |
| --- | --- | ---: | ---: | ---: | --- |
| `AC20-FZK-Haus.ifc` | IFC4 | 127 | 93 | 0 | Nặng về kiến trúc, thiếu tín hiệu O&M |
| `Ifc2x3_Duplex_Architecture.ifc` | IFC2X3 | 295 | 245 | 211 | Có nhiều object kiến trúc, có status từ Revit |
| `Ifc2x3_Duplex_Mechanical.ifc` | IFC2X3 | 529 | 529 | 487 | Phù hợp kiểm tra MEP, có system/status/tag tốt hơn |
| `CuaDai_BIM_Mis 2.ifc` | IFC2X3 | 18,740 | 18,740 | 0 | Kết cấu/Tekla, nhiều assembly/beam/plate, thiếu field O&M |

Ghi chú:

1. `Product sau loại trừ` là số product sau khi bỏ `IfcAnnotation`, `IfcOpeningElement`, `IfcVirtualElement`.
2. `Asset vận hành ứng viên` dựa trên rule hiện có trong `src/ifc/asset_detector.py`: IFC class thuộc nhóm distribution/transport hoặc có property tín hiệu O&M.

### 4.2 IFC Class nghiệp vụ nổi bật

| File | IFC Class nổi bật |
| --- | --- |
| `AC20-FZK-Haus.ifc` | `IfcMember`, `IfcWallStandardCase`, `IfcWindow`, `IfcSpace`, `IfcDoor`, `IfcBeam`, `IfcSlab` |
| `Ifc2x3_Duplex_Architecture.ifc` | `IfcFurnishingElement`, `IfcWallStandardCase`, `IfcWindow`, `IfcSlab`, `IfcSpace`, `IfcDoor`, `IfcCovering`, `IfcBeam` |
| `Ifc2x3_Duplex_Mechanical.ifc` | `IfcFlowSegment`, `IfcFlowFitting`, `IfcSpace`, `IfcEnergyConversionDevice`, `IfcFlowController`, `IfcFlowMovingDevice` |
| `CuaDai_BIM_Mis 2.ifc` | `IfcElementAssembly`, `IfcBeam`, `IfcPlate`, `IfcColumn`, `IfcCovering`, `IfcMember` |

### 4.3 Property Set nổi bật

| File | Property Set nổi bật |
| --- | --- |
| `AC20-FZK-Haus.ifc` | `AC_Pset_Name`, `ArchiCADProperties`, `Pset_BeamCommon`, `Pset_WallCommon`, `Pset_WindowCommon` |
| `Ifc2x3_Duplex_Architecture.ifc` | `PSet_Revit_Other`, `PSet_Revit_Constraints`, `PSet_Revit_Phasing`, `PSet_Revit_Dimensions`, `PSet_Revit_Identity Data` |
| `Ifc2x3_Duplex_Mechanical.ifc` | `PSet_Revit_Constraints`, `PSet_Revit_Identity Data`, `PSet_Revit_Phasing`, `PSet_Revit_Dimensions`, `PSet_Revit_Mechanical`, `PSet_Revit_Other` |
| `CuaDai_BIM_Mis 2.ifc` | `Tekla Assembly`, `Tekla Common`, `Tekla Quantity`, `Pset_MemberCommon`, `Pset_ColumnCommon`, `Pset_BeamCommon` |

### 4.4 Completeness field lõi theo extractor hiện có

| File | Product sau loại trừ | `GlobalId` | `Name` | `Tag` | `Floor` | `Room` | `AssetIdentifier` | `Manufacturer/Model/Serial` | `System` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `AC20-FZK-Haus.ifc` | 93 | 93 | 91 | 82 | 82 | 0 | 0 | 0 | 0 |
| `Ifc2x3_Duplex_Architecture.ifc` | 245 | 245 | 244 | 218 | 157 | 61 | 0 | 38 model only | 0 |
| `Ifc2x3_Duplex_Mechanical.ifc` | 529 | 529 | 528 | 487 | 410 | 77 | 34 | 34 | 487 |
| `CuaDai_BIM_Mis 2.ifc` | 18,740 | 18,740 | 18,740 | 17,864 | 18,737 | 0 | 0 | 0 | 0 |

Nhận xét nhanh:

1. `GlobalId` gần như đầy đủ trên các file mẫu.
2. `Room` thiếu nhiều, đặc biệt file ArchiCAD/Tekla không có room theo extractor hiện tại.
3. Field O&M như `Manufacturer`, `Model`, `SerialNumber`, `AssetIdentifier` chỉ xuất hiện rõ trong file MEP Revit và vẫn còn thấp.
4. File Tekla có nhiều object kết cấu nhưng chưa đủ tín hiệu để tự nhận diện asset vận hành theo rule hiện có.

## 5) Lỗi phổ biến cần ghi nhận

| Nhóm lỗi | Mô tả | Ví dụ trong bối cảnh BIM handover | Ảnh hưởng |
| --- | --- | --- | --- |
| Thiếu metadata | Field vận hành không có giá trị | Thiếu `AssetIdentifier`, `Manufacturer`, `SerialNumber`, `Room` | Không đủ điều kiện import asset vận hành |
| Thừa metadata | Property phục vụ thiết kế/hiển thị quá nhiều | `Constraints`, `Dimensions`, annotation, hatch/presentation | Làm nhiễu mapping và tăng dung lượng payload |
| Sai metadata | Sai kiểu dữ liệu, sai đơn vị, sai format | Ngày tháng text tự do, model/serial bị nhập lẫn | Sai validation và khó đồng bộ DT |
| Sai tên | Tên object là tên mặc định từ authoring tool | Generic family/type name không mang nghĩa vận hành | Khó tìm kiếm, khó nghiệm thu |
| Sai phân loại | IFC Class kỹ thuật chưa map đúng asset type | `IfcFlowSegment` cần tách Pipe/Duct theo system/context | Sai taxonomy vận hành |
| Thiếu Asset ID | Không có mã tài sản chuẩn dự án | Chỉ có `GlobalId` hoặc `Tag` thô | Không đảm bảo unique theo nghiệp vụ |
| Thiếu Location | Không có floor/room/zone rõ ràng | Product nằm ở storey nhưng thiếu room | Không định vị được asset trên DT |
| Thiếu Maintenance Info | Không có thông tin bảo trì | Thiếu warranty, maintenance interval, manual link | Không hỗ trợ vận hành/bảo trì |

## 6) Phân loại lỗi theo nhóm quản trị dữ liệu

| Nhóm | Dấu hiệu kiểm tra | Mức ưu tiên | Rule xử lý ban đầu |
| --- | --- | --- | --- |
| Geometry | Object không có geometry, geometry lỗi, object helper | Trung bình | Chưa loại bỏ nếu vẫn có metadata asset; cần tool geometry riêng để xác nhận |
| Metadata | Field rỗng, trùng nghĩa, sai kiểu, sai đơn vị | Cao | Chuẩn hóa dictionary, giữ `source_property_path`, validate kiểu dữ liệu |
| Classification | IFC Class chưa đủ để suy ra asset vận hành | Cao | Map qua bảng taxonomy, không dùng trực tiếp IFC Class làm `asset_type` nếu chưa được duyệt |
| Asset Code | Thiếu `asset_id`, `tag`, `mark` hoặc không unique | Cao | Dùng Asset ID chuẩn; nếu chưa có thì fallback tạm từ `GlobalId` và đánh dấu cần chuẩn hóa |
| Location | Thiếu floor/room/zone hoặc spatial containment sai | Cao | Bắt buộc tối thiểu `floor`; ưu tiên `room_zone` cho asset trong nhà |
| Maintenance Info | Thiếu manufacturer/model/serial/warranty/manual | Rất cao với MEP | Bắt buộc với asset bảo trì được; đưa vào issue log nếu thiếu |

## 7) Rule ban đầu

### 7.1 Rule đặt tên asset

Mẫu đề xuất cho tên kỹ thuật:

`<AssetType>-<System>-<Location>-<Sequence>`

Ví dụ:

1. `AHU-HVAC-L02-001`
2. `PUMP-CHW-B1-003`
3. `DOOR-ARCH-L05-012`

Quy tắc:

1. `AssetType`, `System`, `Location` dùng mã đã chuẩn hóa.
2. Không dùng khoảng trắng, ký tự đặc biệt khó đồng bộ hoặc tiếng Việt có dấu trong mã kỹ thuật.
3. `asset_name` có thể là tên hiển thị thân thiện, nhưng `asset_id` phải ổn định và unique.
4. Nếu tên từ BIM là tên mặc định của family/type, ghi nhận lỗi `NON_OPERATIONAL_NAME`.

### 7.2 Rule mã hóa Asset ID

Mẫu đề xuất:

`<ProjectCode>-<SiteCode>-<SystemCode>-<AssetTypeCode>-<FloorCode>-<Sequence>`

Ví dụ:

`VSC-S1-HVAC-AHU-L02-001`

Quy tắc:

1. `asset_id` unique trong phạm vi project.
2. Không đổi `asset_id` sau khi asset đã import vào Digital Twin, trừ khi có quy trình migration.
3. Nếu BIM chưa có `asset_id`, cho phép fallback tạm:
   `asset_id = GlobalId`, `status = pending_standardization`.
4. Nếu có cả `AssetIdentifier`, `Tag`, `GlobalId`, ưu tiên:
   `AssetIdentifier` > `Tag/Mark` > `GlobalId`.

### 7.3 Rule phân loại hệ thống

| Mã system | Nhóm hệ thống | Gợi ý nguồn BIM |
| --- | --- | --- |
| `ARCH` | Kiến trúc | Door, Window, Wall, Space |
| `STR` | Kết cấu | Beam, Column, Slab, Plate, Assembly |
| `HVAC` | Điều hòa thông gió | Revit mechanical system, duct/terminal/equipment |
| `EL` | Điện | Cable, panel, light fixture, switch |
| `PLB` | Cấp thoát nước | Pipe, fitting, plumbing equipment |
| `FF` | PCCC | Fire pipe, valve, pump, alarm |
| `SEC` | An ninh | Camera, access control, sensor |
| `LIFT` | Thang máy | Transport element |
| `BMS` | Điều khiển giám sát | Sensor, controller, automation device |

Quy tắc:

1. Không dùng trực tiếp system text từ BIM nếu chưa nằm trong taxonomy.
2. Nếu không xác định được system, ghi `system = null` và issue `MISSING_SYSTEM`.
3. Với MEP asset, `system` là field bắt buộc.

### 7.4 Rule gán vị trí

Thứ tự ưu tiên:

1. `IfcSite`
2. `IfcBuilding`
3. `IfcBuildingStorey`
4. `IfcSpace`
5. Zone/custom location nếu không có `IfcSpace`

Quy tắc:

1. Asset vận hành phải có tối thiểu `floor`.
2. Asset trong nhà nên có `room_zone`.
3. Asset ngoài trời được phép dùng zone thay room.
4. `location` là chuỗi tổng hợp theo dạng:
   `Site > Building > Floor > Room/Zone`.

## 8) Metadata cần giữ, chuẩn hóa, bổ sung, loại bỏ

| Hành động | Metadata | Ghi chú |
| --- | --- | --- |
| Giữ lại | `GlobalId`, `Name`, `Tag`, `ifc_class`, `Type/ObjectType`, `Storey`, `Space/Room`, `System`, `Material`, `Quantity` | Dùng để trace, map và kiểm tra |
| Chuẩn hóa | Field name từ nhiều Pset, đơn vị đo, kiểu dữ liệu, ngày tháng, enum `status/system/asset_type`, format tầng/phòng | Mapping phải giữ nguồn gốc `source_property_path` |
| Bổ sung | `asset_id`, `asset_type`, `system`, `manufacturer`, `model`, `serial_number`, `warranty_start/end/provider`, `maintenance_interval`, `manual_link`, `status` | Ưu tiên asset MEP và asset bảo trì được |
| Loại bỏ khỏi lớp vận hành | Annotation, opening/helper object, property rỗng, placeholder, property trình bày/hatch, revision nội bộ, field trùng nghĩa không được chọn | Có thể vẫn lưu raw metadata riêng nếu cần audit |

## 9) Field tối thiểu cho asset vận hành

| Nhóm | Field DT | Bắt buộc | Nguồn ưu tiên | Rule validation |
| --- | --- | --- | --- | --- |
| Định danh | `asset_id` | Có | `AssetIdentifier`, `Tag`, fallback `GlobalId` | Unique trong project |
| Định danh | `asset_name` | Có | `IfcRoot.Name`, custom name | Không rỗng, không chỉ là placeholder |
| Phân loại | `asset_type` | Có | Custom classification, type name, map từ `ifc_class` | Thuộc taxonomy đã duyệt |
| Phân loại | `ifc_class` | Có | `entity.is_a()` | Không rỗng |
| Hệ thống | `system` | Có với MEP | System assignment, Pset, map theo discipline | Thuộc taxonomy system |
| Vị trí | `floor` | Có | `IfcBuildingStorey.Name` | Không rỗng |
| Vị trí | `room_zone` | Nên có | `IfcSpace.Name`, zone/custom location | Bắt buộc nếu asset nằm trong phòng kỹ thuật |
| Vận hành | `status` | Có | Commissioning/lifecycle/custom Pset | Thuộc enum cho phép |
| Kỹ thuật | `manufacturer` | Nên có | Type identity/custom Pset | Bắt buộc với asset serviceable |
| Kỹ thuật | `model` | Nên có | Model/reference/type name | Bắt buộc với asset serviceable |
| Kỹ thuật | `serial_number` | Nên có | Serial Pset/custom Pset | Bắt buộc với asset serviceable |
| Bảo trì | `warranty` | Nên có | Warranty Pset/custom Pset | Tách được start/end/provider nếu có |
| Bảo trì | `maintenance_info` | Nên có | O&M Pset/manual link | Có interval/team/manual nếu vận hành yêu cầu |

Ngưỡng completeness đề xuất:

1. Field bắt buộc lõi đạt >= 98%.
2. `system` cho MEP đạt >= 95%.
3. Field kỹ thuật/bảo trì cho asset serviceable đạt >= 90%.
4. `room_zone` cho asset trong nhà đạt >= 90%.

## 10) Cấu trúc báo cáo bàn giao

Mỗi đợt khảo sát hoặc import nên xuất một report theo cấu trúc:

1. Thông tin dự án: `project_code`, `site`, `discipline`, package, ngày nhận file.
2. Danh sách file: tên file, định dạng, schema, dung lượng, nguồn export, version.
3. Tóm tắt mô hình: tổng entity, tổng product, product sau loại trừ, asset ứng viên.
4. IFC Class summary: top class nghiệp vụ, class bị loại trừ, class chưa map.
5. Property Set summary: Pset nổi bật, field có thể map, field lạ cần review.
6. Completeness summary: tỷ lệ đủ field tối thiểu theo nhóm asset.
7. Issue summary: lỗi theo Geometry, Metadata, Classification, Asset Code, Location, Maintenance Info.
8. Rule áp dụng: naming, Asset ID, system taxonomy, location mapping, metadata mapping.
9. Kết luận nghiệm thu: đạt/chưa đạt, blocker, danh sách việc cần BIM team bổ sung.
10. Phụ lục: raw issue log, mapping table, sample JSON/CSV/API payload nếu có.

## 11) Kết luận sơ bộ

1. Bộ file mẫu hiện đã đủ để khảo sát IFC kiến trúc, MEP và kết cấu ở mức ban đầu.
2. File Revit/Navisworks native vẫn chưa có, cần bổ sung nếu mục tiêu là đánh giá workflow convert file gốc.
3. IFC MEP Revit là mẫu tốt nhất hiện tại để kiểm thử asset vận hành vì có `system`, `status`, `tag` và một phần thông tin kỹ thuật.
4. Các file ArchiCAD/Tekla có nhiều object hữu ích cho phân loại hình học/kết cấu nhưng thiếu metadata O&M, cần rule bổ sung hoặc checklist yêu cầu nhà thầu.
5. Các rule ban đầu đã đủ để khởi tạo BIM Pipeline: inspect, validate, classify, map, issue log, report handover.
