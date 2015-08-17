var conn = SockJS(['http://', window.location.host, '/realtime/changes'].join(''));

var HomePage = React.createClass({
    getInitialState: function() {
        conn.onmessage = function(e) {
            var d = JSON.parse(e.data);
            console.log(d);
            this.setState({balanceBTC: JSON.parse(d.balanceBTC).result, balancePLN: JSON.parse(d.balancePLN).result}).bind(this);
            return {balanceBTC: 0.0, balancePLN: 0.0};
        };
    },
    render: function() {
        return (
            <div>
                <nav className="navbar navbar-default">
                    <div className="container-fluid">
                        <div className="navbar-header">
                          <button type="button" className="navbar-toggle collapsed" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1" aria-expanded="false">
                            <span className="sr-only">Toggle navigation</span>
                            <span className="icon-bar"></span>
                            <span className="icon-bar"></span>
                            <span className="icon-bar"></span>
                          </button>
                          <a className="navbar-brand" href="#">Brand</a>
                        </div>
                        <div className="collapse navbar-collapse" id="bs-example-navbar-collapse-1">
                            <p className="navbar-text">{this.state.balanceBTC} BTC</p>
                            <p className="navbar-text">{this.state.balancePLN} PLN</p>
                        </div>
                    </div>
                </nav>
            </div>

        );
    }
});

React.render(<HomePage />, document.getElementById('main'));