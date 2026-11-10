import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* Routes to be added in future steps */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
