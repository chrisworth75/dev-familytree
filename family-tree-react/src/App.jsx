import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Nav from './components/Nav'
import Trees from './components/Trees'
import Tree from "./components/Tree.jsx";
import DNA from './components/DNA'
import Search from './components/Search'
import Home from './components/Home'
import MatchDetail from './components/MatchDetail'
import './App.css'


function App() {
    return (
        <BrowserRouter>
            <Nav />
            <main>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/trees" element={<Trees />} />
                    <Route path="/dna" element={<DNA />} />
                    <Route path="/search" element={<Search />} />
                    <Route path="/tree/:id" element={<Tree />} />
                    <Route path="/dna/match/:dnaTestId" element={<MatchDetail />} />
                </Routes>
            </main>
        </BrowserRouter>
    )
}

export default App
