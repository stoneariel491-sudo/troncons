//! La table des points d'entrée de `nvcuda.dll`, chargée une fois par processus.
//!
//! Les noms sont ceux qu'exporte le pilote, tels que `cuda.h` de CUDA 13.1 les choisit par ses
//! `#define` (par exemple `cuMemAlloc` → `cuMemAlloc_v2`, `cuEventElapsedTime` →
//! `cuEventElapsedTime_v2`). Les appels « par flux » (`cuLaunchKernel`, `cuMemcpyHtoDAsync_v2`…)
//! sont pris dans leur forme ordinaire, pas `_ptsz` : le flux par défaut n'est jamais utilisé, chaque
//! opération nomme son flux.
//!
//! Les types suivent `cuda.h` : `CUresult` et `CUdevice` sont des `int`, `CUdeviceptr` un entier de
//! 64 bits, les poignées (`CUcontext`, `CUstream`, `CUevent`, `CUmodule`, `CUfunction`) des pointeurs
//! opaques. Sous Windows x64, la convention `system` est la convention C.

use std::ffi::{c_char, c_int, c_uint, c_void};
use std::sync::OnceLock;

use windows_sys::Win32::System::LibraryLoader::{
    GetProcAddress, LOAD_LIBRARY_SEARCH_SYSTEM32, LoadLibraryExW,
};

pub type CuResult = c_int;
pub type CuDevice = c_int;
pub type CuDevicePtr = u64;
pub type Poignee = *mut c_void;

pub const CUDA_SUCCESS: CuResult = 0;
pub const CUDA_ERROR_NOT_READY: CuResult = 600;
pub const CUDA_ERROR_PRIMARY_CONTEXT_ACTIVE: CuResult = 708;

pub const CU_MEMHOSTALLOC_PORTABLE: c_uint = 0x01;
pub const CU_MEMHOSTALLOC_DEVICEMAP: c_uint = 0x02;
pub const CU_STREAM_NON_BLOCKING: c_uint = 0x1;
pub const CU_EVENT_DEFAULT: c_uint = 0x0;
pub const CU_EVENT_BLOCKING_SYNC: c_uint = 0x1;
pub const CU_EVENT_DISABLE_TIMING: c_uint = 0x2;
pub const CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES: c_int = 8;
pub const CU_JIT_ERROR_LOG_BUFFER: c_int = 5;
pub const CU_JIT_ERROR_LOG_BUFFER_SIZE_BYTES: c_int = 6;

pub const CU_DEVICE_ATTRIBUTE_CAN_MAP_HOST_MEMORY: c_int = 19;
pub const CU_DEVICE_ATTRIBUTE_TCC_DRIVER: c_int = 35;
pub const CU_DEVICE_ATTRIBUTE_ASYNC_ENGINE_COUNT: c_int = 40;
pub const CU_DEVICE_ATTRIBUTE_UNIFIED_ADDRESSING: c_int = 41;
pub const CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR: c_int = 75;
pub const CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR: c_int = 76;

macro_rules! table {
    ($( $champ:ident = $nom:literal : fn($($a:ty),*) ; )*) => {
        /// Les points d'entrée obligatoires. Un symbole absent fait échouer le chargement, avec
        /// son nom : un pilote trop ancien se dit, il ne plante pas plus loin.
        #[allow(non_snake_case)]
        pub struct Api {
            $( pub $champ: unsafe extern "system" fn($($a),*) -> CuResult, )*
            /// `cuEventElapsedTime_v2` (CUDA ≥ 12.8) si présent, sinon la forme d'origine.
            pub cuEventElapsedTime: unsafe extern "system" fn(*mut f32, Poignee, Poignee) -> CuResult,
            /// Version du pilote rendue par `cuDriverGetVersion` (13010 pour CUDA 13.1).
            pub version_pilote: c_int,
        }

        impl Api {
            unsafe fn charger() -> Result<Api, String> {
                let nom_dll: Vec<u16> = "nvcuda.dll\0".encode_utf16().collect();
                // SAFETY : chaîne terminée par un zéro ; recherche limitée à System32, où le
                // pilote d'affichage installe nvcuda.dll (pas de DLL plantée dans le dossier courant).
                let module = unsafe {
                    LoadLibraryExW(nom_dll.as_ptr(), std::ptr::null_mut(), LOAD_LIBRARY_SEARCH_SYSTEM32)
                };
                if module.is_null() {
                    return Err("nvcuda.dll introuvable dans System32 : aucun pilote NVIDIA \
                                installé, ou pilote trop ancien".into());
                }
                let symbole = |nom: &str| -> Result<unsafe extern "system" fn() -> isize, String> {
                    let c = format!("{nom}\0");
                    // SAFETY : module valide, nom terminé par un zéro.
                    unsafe { GetProcAddress(module, c.as_ptr()) }
                        .ok_or_else(|| format!("symbole {nom} absent de nvcuda.dll (pilote trop ancien ?)"))
                };
                let mut api = Api {
                    $( $champ: {
                        let f = symbole($nom)?;
                        // SAFETY : la signature est celle de cuda.h (CUDA 13.1) pour ce symbole.
                        unsafe { std::mem::transmute::<unsafe extern "system" fn() -> isize,
                            unsafe extern "system" fn($($a),*) -> CuResult>(f) }
                    }, )*
                    cuEventElapsedTime: {
                        let f = symbole("cuEventElapsedTime_v2").or_else(|_| symbole("cuEventElapsedTime"))?;
                        // SAFETY : même signature pour les deux formes (float*, CUevent, CUevent).
                        unsafe { std::mem::transmute::<unsafe extern "system" fn() -> isize,
                            unsafe extern "system" fn(*mut f32, Poignee, Poignee) -> CuResult>(f) }
                    },
                    version_pilote: 0,
                };
                // SAFETY : appels documentés sans précondition autre que des pointeurs valides.
                let r = unsafe { (api.cuInit)(0) };
                if r != CUDA_SUCCESS {
                    return Err(format!("cuInit a rendu {r}"));
                }
                let mut v: c_int = 0;
                unsafe { (api.cuDriverGetVersion)(&mut v) };
                api.version_pilote = v;
                Ok(api)
            }
        }
    };
}

table! {
    cuInit = "cuInit" : fn(c_uint);
    cuDriverGetVersion = "cuDriverGetVersion" : fn(*mut c_int);
    cuGetErrorName = "cuGetErrorName" : fn(CuResult, *mut *const c_char);
    cuGetErrorString = "cuGetErrorString" : fn(CuResult, *mut *const c_char);
    cuDeviceGet = "cuDeviceGet" : fn(*mut CuDevice, c_int);
    cuDeviceGetName = "cuDeviceGetName" : fn(*mut c_char, c_int, CuDevice);
    cuDeviceGetAttribute = "cuDeviceGetAttribute" : fn(*mut c_int, c_int, CuDevice);
    cuDevicePrimaryCtxRetain = "cuDevicePrimaryCtxRetain" : fn(*mut Poignee, CuDevice);
    cuDevicePrimaryCtxRelease = "cuDevicePrimaryCtxRelease_v2" : fn(CuDevice);
    cuDevicePrimaryCtxSetFlags = "cuDevicePrimaryCtxSetFlags_v2" : fn(CuDevice, c_uint);
    cuDevicePrimaryCtxGetState = "cuDevicePrimaryCtxGetState" : fn(CuDevice, *mut c_uint, *mut c_int);
    cuCtxSetCurrent = "cuCtxSetCurrent" : fn(Poignee);
    cuCtxSynchronize = "cuCtxSynchronize" : fn();
    cuCtxGetStreamPriorityRange = "cuCtxGetStreamPriorityRange" : fn(*mut c_int, *mut c_int);
    cuMemGetInfo = "cuMemGetInfo_v2" : fn(*mut usize, *mut usize);
    cuStreamCreateWithPriority = "cuStreamCreateWithPriority" : fn(*mut Poignee, c_uint, c_int);
    cuStreamWaitEvent = "cuStreamWaitEvent" : fn(Poignee, Poignee, c_uint);
    cuStreamSynchronize = "cuStreamSynchronize" : fn(Poignee);
    cuStreamQuery = "cuStreamQuery" : fn(Poignee);
    cuStreamDestroy = "cuStreamDestroy_v2" : fn(Poignee);
    cuEventCreate = "cuEventCreate" : fn(*mut Poignee, c_uint);
    cuEventRecord = "cuEventRecord" : fn(Poignee, Poignee);
    cuEventQuery = "cuEventQuery" : fn(Poignee);
    cuEventSynchronize = "cuEventSynchronize" : fn(Poignee);
    cuEventDestroy = "cuEventDestroy_v2" : fn(Poignee);
    cuMemAlloc = "cuMemAlloc_v2" : fn(*mut CuDevicePtr, usize);
    cuMemFree = "cuMemFree_v2" : fn(CuDevicePtr);
    cuMemHostAlloc = "cuMemHostAlloc" : fn(*mut *mut c_void, usize, c_uint);
    cuMemFreeHost = "cuMemFreeHost" : fn(*mut c_void);
    cuMemHostGetDevicePointer = "cuMemHostGetDevicePointer_v2" : fn(*mut CuDevicePtr, *mut c_void, c_uint);
    cuMemcpyHtoDAsync = "cuMemcpyHtoDAsync_v2" : fn(CuDevicePtr, *const c_void, usize, Poignee);
    cuMemcpyDtoHAsync = "cuMemcpyDtoHAsync_v2" : fn(*mut c_void, CuDevicePtr, usize, Poignee);
    cuMemcpyDtoDAsync = "cuMemcpyDtoDAsync_v2" : fn(CuDevicePtr, CuDevicePtr, usize, Poignee);
    cuMemsetD8Async = "cuMemsetD8Async" : fn(CuDevicePtr, u8, usize, Poignee);
    cuModuleLoadDataEx = "cuModuleLoadDataEx" : fn(*mut Poignee, *const c_void, c_uint, *mut c_int, *mut *mut c_void);
    cuModuleUnload = "cuModuleUnload" : fn(Poignee);
    cuModuleGetFunction = "cuModuleGetFunction" : fn(*mut Poignee, Poignee, *const c_char);
    cuFuncSetAttribute = "cuFuncSetAttribute" : fn(Poignee, c_int, c_int);
    cuLaunchKernel = "cuLaunchKernel" : fn(Poignee, c_uint, c_uint, c_uint, c_uint, c_uint, c_uint, c_uint, Poignee, *mut *mut c_void, *mut *mut c_void);
}

static API: OnceLock<Result<Api, String>> = OnceLock::new();

/// La table, chargée au premier appel. Une erreur de chargement est gardée et rendue à chaque appel.
pub fn api() -> Result<&'static Api, String> {
    // SAFETY : chargement d'une DLL système et lecture de ses symboles, une seule fois.
    match API.get_or_init(|| unsafe { Api::charger() }) {
        Ok(a) => Ok(a),
        Err(e) => Err(e.clone()),
    }
}
