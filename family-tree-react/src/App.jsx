import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom'
import Nav from './components/Nav'
import Trees from './components/Trees'
import Tree from "./components/Tree.jsx";
import DNA from './components/DNA'
import Search from './components/Search'
import Home from './components/Home'
import MatchDetail from './components/MatchDetail'
import PersonDetail from './components/PersonDetail'
import Photos from './components/Photos'
import TierBanner from './components/TierBanner'
import './App.css'

function NavLayout() {
    return (
        <>
            <Nav />
            <main><Outlet /></main>
        </>
    )
}

function App() {
    return (
        <BrowserRouter>
            <TierBanner />
            <Routes>
                <Route path="/tree/:id" element={<Tree />} />
                <Route element={<NavLayout />}>
                    <Route path="/" element={<Home />} />
                    <Route path="/trees" element={<Trees />} />
                    <Route path="/dna" element={<DNA />} />
                    <Route path="/search" element={<Search />} />
                    <Route path="/dna/match/:dnaTestId" element={<MatchDetail />} />
                    <Route path="/person/:id" element={<PersonDetail />} />
                    <Route path="/photos" element={<Photos />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
