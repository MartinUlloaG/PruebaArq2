import { Navigate, Route, Routes } from 'react-router-dom'

import Marco from './vistas/Marco'
import RutaProtegida from './vistas/RutaProtegida'
import VistaIngreso from './vistas/VistaIngreso'
import VistaInicio from './vistas/VistaInicio'
import VistaInventario from './vistas/VistaInventario'
import VistaPedidos from './vistas/VistaPedidos'
import VistaUsuarios from './vistas/VistaUsuarios'

export default function App() {
  return (
    <Routes>
      <Route path="/ingresar" element={<VistaIngreso />} />
      <Route
        element={
          <RutaProtegida>
            <Marco />
          </RutaProtegida>
        }
      >
        <Route index element={<VistaInicio />} />
        <Route
          path="pedidos"
          element={
            <RutaProtegida roles={['cliente']}>
              <VistaPedidos />
            </RutaProtegida>
          }
        />
        <Route
          path="inventario"
          element={
            <RutaProtegida roles={['operador', 'administrador']}>
              <VistaInventario />
            </RutaProtegida>
          }
        />
        <Route
          path="usuarios"
          element={
            <RutaProtegida roles={['administrador']}>
              <VistaUsuarios />
            </RutaProtegida>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
