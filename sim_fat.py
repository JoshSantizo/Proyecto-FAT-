import json
import os
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, ttk
from configuracion import TAMAÑO_BLOQUE, DIR_FAT, DIR_DATOS, PROPIETARIO_DEFECTO, RUTA_USUARIOS 

#Principal

class SistemaFAT:
    def __init__(self):
        os.makedirs(DIR_FAT, exist_ok=True)
        os.makedirs(DIR_DATOS, exist_ok=True)
        self.usuarios_registrados = {PROPIETARIO_DEFECTO}
        self.usuario_actual = PROPIETARIO_DEFECTO
        self._cargar_usuarios = lambda: {PROPIETARIO_DEFECTO}
        self._guardar_usuarios = lambda: None

    def _guardar_entrada_fat(self, nombre_archivo, entrada):
        ruta = os.path.join(DIR_FAT, f"{nombre_archivo}.json")
        with open(ruta, 'w') as f:
            json.dump(entrada, f, indent=4)

    def _cargar_entrada_fat(self, nombre_archivo):
        ruta = os.path.join(DIR_FAT, f"{nombre_archivo}.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, 'r') as f:
            return json.load(f)

    def _generar_bloques(self, contenido):
        return [f"ruta_temporal_a_bloque_{int(time.time())}"] 

    def crear_archivo(self, nombre_archivo, contenido, propietario=PROPIETARIO_DEFECTO):
        if self._cargar_entrada_fat(nombre_archivo):
            return False, "Error: El archivo ya existe."

        rutas_bloques = self._generar_bloques(contenido)
        if not rutas_bloques:
            return False, "Error: El contenido del archivo es inválido."

        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entrada_fat = {
            "nombre": nombre_archivo,
            "ruta_datos_inicial": rutas_bloques[0],
            "estado_papelera": False,
            "cant_caracteres": len(contenido),
            "fecha_creacion": ahora,
            "fecha_modificacion": ahora,
            "fecha_eliminacion": None,
            "propietario": propietario,
            "permisos": {"lectura": [propietario], "escritura": [propietario]}
        }
        self._guardar_entrada_fat(nombre_archivo, entrada_fat)
        return True, "Archivo creado exitosamente."

    def listar_archivos(self, incluir_eliminados=False):
        archivos = []
        for nombre_archivo_json in os.listdir(DIR_FAT):
            if nombre_archivo_json.endswith(".json"):
                nombre = nombre_archivo_json.replace(".json", "")
                entrada = self._cargar_entrada_fat(nombre)
                if entrada and (incluir_eliminados or not entrada.get("estado_papelera", False)):
                    archivos.append(entrada)
        return archivos

    # Funciones que necesito probar y trabajar con la interfaz
    def obtener_contenido_archivo(self, nombre_archivo): return None, "No implementado"
    def modificar_archivo(self, nombre_archivo, nuevo_contenido): return False, "No implementado"
    def eliminar_archivo(self, nombre_archivo): return False, "No implementado"


#INterfaz

class InterfazFAT:
    def __init__(self, master):
        self.master = master
        self.sistema_fat = SistemaFAT()
        self.master.title("Simulador FAT")
        self.var_usuario_actual = tk.StringVar(master, value=PROPIETARIO_DEFECTO)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configurar_interfaz()
        self._mostrar_dialogo_login()

    def _centrar_ventana(self, ventana, ancho=None, alto=None):
        ventana.update_idletasks()
        w = ancho if ancho else ventana.winfo_width()
        h = alto if alto else ventana.winfo_height()
        ws = ventana.winfo_screenwidth()
        hs = ventana.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        ventana.geometry(f'{w}x{h}+{x}+{y}')
        ventana.transient(self.master)
        ventana.grab_set()

    def _cambiar_usuario_en_sistema(self, nuevo_usuario):
        self.sistema_fat.usuario_actual = nuevo_usuario
        self.var_usuario_actual.set(nuevo_usuario)
        self.master.title(f"Simulador FAT - Usuario: {nuevo_usuario}")
        self.actualizar_lista_archivos()

    def _mostrar_dialogo_login(self):
        usuario = simpledialog.askstring("Inicio de Sesión", "Ingrese su nombre de usuario:")
        if not usuario:
            self.master.quit()
            return

        self._cambiar_usuario_en_sistema(usuario.strip().lower())
        self.master.deiconify()

    def _configurar_interfaz(self):
        frame_usuario = ttk.Frame(self.master, padding=10)
        frame_usuario.pack(fill='x')

        ttk.Label(frame_usuario, text="Usuario Actual:").pack(side=tk.LEFT)
        ttk.Label(frame_usuario, textvariable=self.var_usuario_actual).pack(side=tk.LEFT)

        frame_lista = ttk.LabelFrame(self.master, text="Archivos en el Sistema", padding=10)
        frame_lista.pack(padx=10, pady=5, fill='both', expand=True)
        self.lista_archivos_box = tk.Listbox(frame_lista, height=15)
        self.lista_archivos_box.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_archivos_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.lista_archivos_box.config(yscrollcommand=scrollbar.set)
        frame_botones = ttk.Frame(self.master, padding=5)
        frame_botones.pack(fill='x')
        ttk.Button(frame_botones, text="Crear Archivo", command=self.gui_crear_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        self.actualizar_lista_archivos()

    def actualizar_lista_archivos(self, incluir_eliminados=False):
        self.lista_archivos_box.delete(0, tk.END)
        archivos = self.sistema_fat.listar_archivos(incluir_eliminados=incluir_eliminados)
        for i, entrada_archivo in enumerate(archivos):
            display_text = f"[OK] {entrada_archivo['nombre']} (Propietario: {entrada_archivo['propietario']})"
            self.lista_archivos_box.insert(i, display_text)

    def obtener_nombre_archivo_seleccionado(self):
        indices_seleccionados = self.lista_archivos_box.curselection()
        if not indices_seleccionados:
            messagebox.showwarning("Selección", "Por favor, selecciona un archivo de la lista.")
            return None
        texto_seleccionado = self.lista_archivos_box.get(indices_seleccionados[0]).split('(Propietario:')[0].strip()
        return ' '.join(texto_seleccionado.split()[1:]).strip()

    def gui_crear_archivo(self):
        nombre_archivo = simpledialog.askstring("Crear Archivo", "Introduce el nombre del archivo:")
        if not nombre_archivo: return
        contenido = simpledialog.askstring("Crear Archivo", f"Introduce el contenido de '{nombre_archivo}':", initialvalue="Contenido de prueba")
        if contenido is None: return

        exito, mensaje = self.sistema_fat.crear_archivo(nombre_archivo, contenido, propietario=self.sistema_fat.usuario_actual)
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.actualizar_lista_archivos()
        else:
            messagebox.showerror("Error", mensaje)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Simulador FAT - Inicializando...")
    app = InterfazFAT(root)
    root.mainloop()