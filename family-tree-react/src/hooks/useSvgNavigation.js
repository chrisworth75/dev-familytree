import { useNavigate } from 'react-router-dom';

export function useSvgNavigation() {
    const navigate = useNavigate();
    return (e) => {
        const link = e.target.closest('a');
        if (link) {
            const href = link.getAttribute('href') || link.getAttribute('xlink:href');
            if (href && href.startsWith('/person/')) {
                e.preventDefault();
                navigate(href);
            }
        }
    };
}
