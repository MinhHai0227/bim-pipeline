# BIM Handover Standard for Digital Twin v1

## 1. Muc dich va pham vi

Tai lieu nay quy dinh chuan dau vao BIM handover tu giai doan xay dung sang van hanh, lam co so nap du lieu vao nen tang Digital Twin.

Pham vi ap dung:

1. File nguon IFC, Revit export sang IFC, va cac bo du lieu asset lien quan.
2. Asset phuc vu van hanh, bao tri, khai thac.
3. Khong uu tien cac doi tuong chi phuc vu trinh bay, chu thich, mo hinh hoa thiet ke.

Muc tieu:

1. Chuan hoa bo thong tin toi thieu cho asset van hanh.
2. Chuan hoa quy tac dat ten, ma hoa, phan loai va dinh vi asset.
3. Tao bang mapping tu BIM Property sang Digital Twin Property.
4. Xac dinh metadata can giu, can chuan hoa, can bo sung va can loai bo.
5. Chuan hoa pipeline xu ly truoc khi import vao Digital Twin.

## 2. Nguyen tac chung

1. Moi asset van hanh phai co dinh danh duy nhat.
2. Uu tien du lieu phuc vu van hanh thay vi du lieu chi phuc vu thiet ke.
3. IFC Class khong tu dong dong nghia voi Asset Type van hanh, can co lop mapping.
4. Vi tri asset phai duoc gan toi thieu den tang; uu tien den phong/zone neu co.
5. Thuoc tinh trung lap phai co quy tac uu tien nguon.
6. Truong khong co gia tri phai de `null` hoac rong theo schema thong nhat, khong tu y sinh text placeholder.

## 3. Danh sach truong thong tin toi thieu cho asset van hanh

Day la danh sach field toi thieu de chap nhan handover vao Digital Twin.

| DT Property | Mo ta | Bat buoc | Kieu du lieu | Ghi chu |
| --- | --- | --- | --- | --- |
| `asset_id` | Ma tai san van hanh duy nhat | Co | string | Theo quy tac ma hoa Asset ID |
| `asset_name` | Ten hien thi tai san | Co | string | Lay tu ten doi tuong hoac ten da chuan hoa |
| `asset_type` | Loai tai san van hanh | Co | string | Vi du: AHU, Pump, Beam, Door, Valve |
| `ifc_class` | Lop IFC goc | Co | string | Vi du: `IfcFlowTerminal`, `IfcBeam` |
| `system` | He thong ky thuat hoac nhom he thong | Co voi asset thuoc he thong | string | Vi du: HVAC, Fire Fighting, Electrical |
| `location` | Chuoi vi tri tong hop | Co | string | Vi du: Building A > Level 2 > Room 201 |
| `floor` | Tang | Co | string | Vi du: Level 1, Basement 2 |
| `room_zone` | Phong hoac zone | Nen co | string | Neu khong co de `null` |
| `manufacturer` | Hang san xuat | Nen co | string | Ap dung manh cho MEP va thiet bi |
| `model` | Model/type code | Nen co | string | Co the lay tu type identity data |
| `serial_number` | So serial | Nen co | string | Asset serviceable bat buoc nen co |
| `warranty` | Thong tin bao hanh | Nen co | object/string | Co the tach thanh start/end/provider |
| `maintenance_info` | Thong tin bao tri | Nen co | object/string | Chu ky, nhom bao tri, manual link |
| `status` | Trang thai handover/operation | Co | string | `planned`, `installed`, `commissioned`, `active`, `inactive` |

## 4. Quy tac dat ten va ma hoa

### 4.1 Quy tac dat ten doi tuong

Ten doi tuong van hanh nen theo cau truc:

`<AssetType>-<System>-<Location>-<Sequence>`

Vi du:

1. `AHU-HVAC-B2-001`
2. `PUMP-CHW-L1-003`
3. `DOOR-ARCH-L2-015`

Quy tac:

1. Viet hoa khong dau cho ma quy uoc.
2. Khong dung khoang trang trong ma ky thuat.
3. Ten hien thi (`asset_name`) co the than thien hon, nhung `asset_id` phai theo chuan.
4. Khong dung ten mac dinh cua authoring tool lam ten van hanh neu ten do khong co nghia nghiep vu.

### 4.2 Quy tac ma hoa Asset ID

Mau de xuat:

`<ProjectCode>-<SiteCode>-<SystemCode>-<AssetTypeCode>-<FloorCode>-<Sequence>`

Vi du:

`VSC-S1-HVAC-AHU-L02-001`

Thanh phan:

1. `ProjectCode`: ma du an.
2. `SiteCode`: ma khu, toa, block.
3. `SystemCode`: ma he thong.
4. `AssetTypeCode`: ma loai asset.
5. `FloorCode`: ma tang.
6. `Sequence`: so thu tu duy nhat trong cung nhom.

Quy tac uniqueness:

1. `asset_id` duy nhat trong pham vi toan du an.
2. Neu BIM chua co `asset_id`, cho phep sinh tam tu `GlobalId`, nhung trang thai phai danh dau `pending_standardization`.

### 4.3 Quy tac phan loai he thong

Danh muc he thong toi thieu:

1. `ARCH`: kien truc.
2. `STR`: ket cau.
3. `HVAC`: thong gio dieu hoa.
4. `EL`: dien.
5. `PLB`: cap thoat nuoc.
6. `FF`: phong chay chua chay.
7. `SEC`: an ninh.
8. `LIFT`: thang may.
9. `BMS`: he dieu khien va giam sat.

Quy tac:

1. Moi asset phai map ve mot `system` chuan neu asset thuoc he thong ky thuat.
2. Asset kien truc/ket cau duoc phep map vao `ARCH` hoac `STR`.
3. Khong dung truc tiep ten system tu tool authoring neu chua duoc quy chuan.

### 4.4 Quy tac gan vi tri

Thu tu uu tien gan vi tri:

1. `Site`
2. `Building`
3. `Storey/Floor`
4. `Space/Room`
5. `Zone` neu khong co `Space`

Quy tac:

1. Asset van hanh phai co it nhat `floor`.
2. Asset trong phong ky thuat, phong may, khu vuc van hanh nen co `room_zone`.
3. Asset ngoai troi co the dung `zone` thay cho `room`.
4. `location` la truong tong hop tu cap vi tri da chuan hoa.

## 5. Bang mapping tu BIM Property sang Digital Twin Property

Nguyen tac mapping:

1. Uu tien property mang nghia van hanh ro rang hon property tong quat.
2. Neu co nhieu nguon cho cung mot field, uu tien theo thu tu:
   `custom handover pset` > `type identity data` > `common pset` > `authoring tool pset` > `ifc native fallback`
3. Giu lai `source_property_path` de trace nguon.

| Digital Twin Property | IFC / BIM Source uu tien | Vi du nguon |
| --- | --- | --- |
| `asset_id` | `PSet_*.*AssetIdentifier*`, `Tag`, custom handover pset | `PSet_Revit_Other.AssetIdentifier`, `IfcElement.Tag` |
| `asset_name` | `Name`, custom naming pset | `IfcRoot.Name` |
| `asset_type` | custom classification, type name, mapped from `ifc_class` | `IfcBeam` -> `Beam` |
| `ifc_class` | IFC native | `entity.is_a()` |
| `system` | system assignment, classification, custom pset | `IfcRelServicesBuildings`, Revit system name |
| `location` | spatial hierarchy hop nhat | `Site > Building > Storey > Space` |
| `floor` | spatial container | `IfcBuildingStorey.Name` |
| `room_zone` | `IfcSpace.Name`, zone assignment | `IfcSpace.Name` |
| `manufacturer` | manufacturer property | `PSet_Revit_Type_Identity Data.Manufacturer` |
| `model` | model/type/reference property | `Model`, `Reference`, type name |
| `serial_number` | serial property | `PSet_Revit_Other.SerialNumber` |
| `warranty` | warranty pset/custom pset | `WarrantyStartDate`, `WarrantyDurationParts` |
| `maintenance_info` | O&M pset/custom pset/manual link | `ExpectedLife`, `MaintenanceInterval`, manual URL |
| `status` | commissioning / lifecycle / custom pset | `Phase Created`, `OperationalStatus` |

## 6. Metadata rules

### 6.1 Metadata can giu lai

1. `GlobalId`
2. `Name`
3. `Tag`
4. `ifc_class`
5. `Type/ObjectType`
6. `Storey`
7. `Space/Room`
8. `System`
9. `Manufacturer`
10. `Model`
11. `SerialNumber`
12. `Warranty`
13. `InstallationDate`
14. `Status`
15. Quan he type, material, spatial containment

### 6.2 Metadata can chuan hoa

1. Ten field tu cac PSet khac nhau ve mot schema chung.
2. Don vi do ve chuan du an.
3. Kieu du lieu:
   string, number, boolean, date.
4. Format ngay thang theo ISO 8601.
5. Gia tri enum nhu `status`, `system`, `asset_type`.
6. Cach ghi tang, phong, zone.

### 6.3 Metadata can bo sung

1. `asset_id` neu chua co.
2. `asset_type` van hanh neu IFC Class chua du.
3. `system` cho asset MEP.
4. `manufacturer`, `model`, `serial_number` cho asset bao tri duoc.
5. `warranty_start`, `warranty_end`, `warranty_provider`.
6. `maintenance_interval`
7. `maintenance_team`
8. `manual_link`
9. `status`

### 6.4 Metadata can loai bo hoac khong dua vao lop van hanh

1. Thuoc tinh chi phuc vu ve ky hoa, annotation, hatch, presentation.
2. Thuoc tinh hinh hoc chi tiet khong dung cho van hanh.
3. Thuoc tinh trung lap cung nghia nhung khac ten.
4. Thuoc tinh rong, placeholder, gia tri mac dinh vo nghia.
5. Thuoc tinh chuyen cho tac gia mo hinh, revision noi bo, thong tin draft.

## 7. Tieu chi chap nhan du lieu handover

### 7.1 Do day du thong tin

1. `asset_id`, `asset_name`, `asset_type`, `ifc_class`, `floor`, `status` dat >= 98%.
2. `system` dat >= 95% voi asset MEP.
3. `manufacturer`, `model`, `serial_number`, `warranty` dat >= 90% voi asset can bao tri.
4. `room_zone` dat >= 90% cho asset nam trong khong gian trong nha.

### 7.2 Do nhat quan

1. 100% `asset_id` duy nhat.
2. 100% `status` thuoc danh muc cho phep.
3. 100% `system` thuoc taxonomy he thong duoc phe duyet.
4. 100% field date dung dinh dang quy uoc.

### 7.3 Quy tac loai tru

Loai ra khoi lop asset van hanh:

1. `IfcAnnotation`
2. `IfcOpeningElement`
3. `IfcVirtualElement`
4. Doi tuong chi la geometry helper, construction aid, hay note object

## 8. BIM Pipeline cho Digital Twin

```mermaid
flowchart LR
    A[Upload / Input File]
    B[Inspect]
    C[Validate]
    D[Clean]
    E[Map]
    F[Export]
    G[Review]
    H[Import Digital Twin]

    A --> B --> C --> D --> E --> F --> G --> H
```

Mo ta buoc:

1. `Upload / Input File`: nhan IFC va tai lieu handover lien quan.
2. `Inspect`: doc schema, class, pset, spatial structure, quantity.
3. `Validate`: kiem tra completeness, uniqueness, type, naming, taxonomy.
4. `Clean`: loai bo metadata thua, gop field trung lap, xu ly null/placeholder.
5. `Map`: map BIM Property sang Digital Twin schema.
6. `Export`: xuat JSON/CSV/API payload theo schema DT.
7. `Review`: nghiem thu nghiep vu va ky thuat.
8. `Import Digital Twin`: nap vao twin graph / asset registry / maintenance platform.

## 9. Bang taxonomy van hanh toi thieu

| IFC Class | Asset Type goi y | System mac dinh |
| --- | --- | --- |
| `IfcBeam` | Beam | `STR` |
| `IfcColumn` | Column | `STR` |
| `IfcWall` / `IfcWallStandardCase` | Wall | `ARCH` |
| `IfcSlab` | Slab | `STR` / `ARCH` |
| `IfcDoor` | Door | `ARCH` |
| `IfcWindow` | Window | `ARCH` |
| `IfcFlowSegment` | Pipe/Duct Segment | `PLB` / `HVAC` |
| `IfcFlowFitting` | Pipe/Duct Fitting | `PLB` / `HVAC` |
| `IfcFlowTerminal` | Terminal Device | `HVAC` / `EL` |
| `IfcFlowController` | Valve/Controller | `PLB` / `HVAC` / `FF` |
| `IfcFlowMovingDevice` | Pump/Fan | `PLB` / `HVAC` |
| `IfcUnitaryEquipment` | AHU/FCU/Package Unit | `HVAC` |

## 10. Mau schema xuat cho Digital Twin

```json
{
  "asset_id": "VSC-S1-HVAC-AHU-L02-001",
  "asset_name": "AHU Tang 2 Khu A",
  "asset_type": "AHU",
  "ifc_class": "IfcUnitaryEquipment",
  "system": "HVAC",
  "location": "Site A > Building 1 > Level 2 > AHU Room",
  "floor": "Level 2",
  "room_zone": "AHU Room",
  "manufacturer": "Daikin",
  "model": "AHU-1200",
  "serial_number": "SN-2026-0001",
  "warranty": {
    "start_date": "2026-01-15",
    "end_date": "2027-01-15",
    "provider": "Daikin VN"
  },
  "maintenance_info": {
    "interval_days": 90,
    "team": "MEP Operations",
    "manual_link": "https://example.local/manuals/ahu-1200.pdf"
  },
  "status": "commissioned"
}
```

## 11. Governance va trach nhiem

1. Nha thau/BIM Coordinator:
   dam bao mo hinh va metadata ban giao dat chuan.
2. FM/Operations Team:
   xac nhan field can thiet cho van hanh va nghiem thu nghiep vu.
3. Data/Platform Team:
   xay dung rule validate, map, import, va audit quality.
4. Product Owner Digital Twin:
   phe duyet taxonomy, schema, va nguong acceptance.

## 12. Phien ban va thay doi

- Version: `v1`
- Trang thai: `Draft for adoption`
- Muc dich: dung lam chuan dau vao ban dau cho BIM handover sang Digital Twin

