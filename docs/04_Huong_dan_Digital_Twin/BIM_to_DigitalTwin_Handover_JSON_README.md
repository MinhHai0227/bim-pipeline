# BIM to Digital Twin Handover JSON - Tower A Template

File JSON này dùng làm mẫu chuyển giao dữ liệu từ BIM/IFC/COBie sang Digital Twin Platform.

Các phần chính:
1. facility: thông tin công trình.
2. floors/spaces/zones: cấu trúc không gian.
3. assets: danh mục thiết bị/tài sản vận hành.
4. devices: thiết bị/gateway/controller dùng để kết nối BMS/IoT/VMS/CMMS.
5. points: điểm dữ liệu realtime/status/alarm/command.
6. integrations: cấu hình kết nối với BMS, IoT/DMP, VMS, CMMS.
7. validation_rules: quy tắc kiểm tra trước khi import.
8. handover_checklist: checklist bàn giao.

Khóa mapping quan trọng:
- ifc_guid: khóa từ mô hình IFC để chọn đúng object 3D/BIM.
- asset_id: khóa master của Digital Twin Asset Registry.
- device_id: khóa kết nối sang BMS/IoT.
- point_id: khóa từng tín hiệu telemetry/status/alarm/command.
- cmms_asset_id: khóa đồng bộ sang hệ thống bảo trì.

Không nên dùng tên thiết bị làm khóa chính vì tên có thể trùng hoặc bị đổi.