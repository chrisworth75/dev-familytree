import { NavLink } from 'react-router-dom'

function Nav() {
    return (
        <nav className="nav">
            <div className="nav-brand">Family Tree</div>
            <div className="nav-links">
                <NavLink to="/">Home</NavLink>
                <NavLink to="/trees">Trees</NavLink>
                <NavLink to="/dna">DNA Matches</NavLink>
                <NavLink to="/search">Search</NavLink>
                <NavLink to="/photos">Photos</NavLink>
            </div>
        </nav>
    )
}

export default Nav
