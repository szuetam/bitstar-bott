var conn = SockJS(['http://', window.location.host, '/realtime/changes'].join(''));

var types = {
    open_orders: function(data) {
        return data;
    },
    balance: function(data) {
        this.setState({balanceBTC: JSON.parse(data.balanceBTC).result, balancePLN: JSON.parse(data.balancePLN).result});
        return
    },
    beacon: function(data) {
        this.setState({beacon: new Date().getTime()});
    }
};

function updateLiveIndicator(timestamp) {
}

var BalanceBar = React.createClass({
    render: function() {
        return (
            <div className="collapse navbar-collapse" id="bs-example-navbar-collapse-1">
                <p className="navbar-text">{this.props.balanceBTC} BTC</p>
                <p className="navbar-text">{this.props.balancePLN} PLN</p>
            </div>
        );
    }
});

var LiveIndicator = React.createClass({
    render: function() {
        return (
            <div id="trans-rect" className="navbar-brand live_indicator offline"></div>
        );
    },
    componentDidMount: function() {
        this._tick();
    },
    _tick: function() {
        this.interval = setTimeout(function() {
            var now = new Date().getTime();
            var last_seen = now - this.props.beacon;
            console.log('Last seen ', last_seen);
            console.log('Beacon ', this.props.beacon);
            var node = $(React.findDOMNode(this));
            node.removeClass('online possible_offline offline');
            if (last_seen <= 10000) {
                node.addClass('online');
            } else if (last_seen > 10000 && last_seen < 20000) {
                node.addClass('possible_offline');
            } else if (last_seen >= 20000) {
                node.addClass('offline');
            }
            this._tick();
        }.bind(this), 3000);
    }
});

var NavBar = React.createClass({
    render: function() {
        return (
            <nav className="navbar navbar-default">
                <div className="container-fluid">
                    <div className="navbar-header">
                        <button type="button" className="navbar-toggle collapsed" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1" aria-expanded="false">
                            <span className="sr-only">Toggle navigation</span>
                            <span className="icon-bar"></span>
                            <span className="icon-bar"></span>
                            <span className="icon-bar"></span>
                        </button>
                        <a className="navbar-brand" href="#"><LiveIndicator beacon={this.props.beacon} /> BtstrVolumeBot</a>
                    </div>
                    <BalanceBar balanceBTC={this.props.balanceBTC} balancePLN={this.props.balancePLN}/>
                </div>
            </nav>
        );
    }
});

var HomePage = React.createClass({
    getInitialState: function() {
        conn.onmessage = function(e) {
            var d = JSON.parse(e.data);
            //console.log(d);
            types[d.type].bind(this)(d);

        }.bind(this);
        return {balanceBTC: 0.0, balancePLN: 0.0, open_orders: [], 'beacon': 0};
    },
    render: function() {
        return (
            <div>
                <NavBar balanceBTC={this.state.balanceBTC} balancePLN={this.state.balancePLN} beacon={this.state.beacon}/>
            </div>
        );
    }
});

React.render(<HomePage />, document.getElementById('main'));