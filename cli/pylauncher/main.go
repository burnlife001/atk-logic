// python3.14 launcher — loads embedded Python 3.14 and runs a script.
// Build: go build -o python3.14.exe
//
// Simple: just Py_Main. All decoder init is in Python via ctypes.
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"unsafe"
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		fmt.Fprintln(os.Stderr, "cannot find executable path:", err)
		os.Exit(1)
	}
	exeDir := filepath.Dir(exe)
	libDir := filepath.Join(exeDir, "..", "lib")

	if env := os.Getenv("ATK_LIB_DIR"); env != "" {
		libDir = env
	}

	libDir, err = filepath.Abs(libDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "cannot resolve lib dir:", err)
		os.Exit(1)
	}
	binDir := filepath.Join(libDir, "bin")
	projectRoot := filepath.Dir(libDir)

	path := os.Getenv("PATH")
	os.Setenv("PATH", binDir+string(filepath.ListSeparator)+path)

	kernel32, _ := syscall.LoadLibrary("kernel32.dll")
	if kernel32 != 0 {
		setDllDir, _ := syscall.GetProcAddress(kernel32, "SetDllDirectoryW")
		if setDllDir != 0 {
			binDirW, _ := syscall.UTF16PtrFromString(binDir)
			syscall.SyscallN(setDllDir, uintptr(unsafe.Pointer(binDirW)))
		}
	}

	os.Setenv("PYTHONHOME", projectRoot)

	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: python3.14.exe <script.py> [args...]")
		os.Exit(1)
	}

	// Load libsigrokdecode-4.dll early so it's available to Python ctypes
	srdPath := filepath.Join(binDir, "libsigrokdecode-4.dll")
	syscall.LoadLibrary(srdPath)

	pyDllPath := filepath.Join(binDir, "libpython3.14.dll")
	pyDll, err := syscall.LoadLibrary(pyDllPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "cannot load %s: %v\n", pyDllPath, err)
		os.Exit(1)
	}

	pyMain, err := syscall.GetProcAddress(pyDll, "Py_Main")
	if err != nil {
		fmt.Fprintln(os.Stderr, "Py_Main not found")
		os.Exit(1)
	}

	argv := make([]*uint16, len(os.Args))
	for i, a := range os.Args {
		argv[i], _ = syscall.UTF16PtrFromString(a)
	}

	ret, _, _ := syscall.SyscallN(pyMain, uintptr(len(os.Args)), uintptr(unsafe.Pointer(&argv[0])))
	os.Exit(int(ret))
}
